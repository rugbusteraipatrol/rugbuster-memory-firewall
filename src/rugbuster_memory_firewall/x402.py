"""x402 payment configuration and settlement evidence for the paid API."""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from cdp.x402.x402 import create_cdp_auth_headers
from fastapi import FastAPI
from x402.http import AuthHeaders, FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import SupportedResponse
from x402.schemas.responses import SupportedKind
from x402.server import x402ResourceServer

CDP_FACILITATOR_URL = "https://api.cdp.coinbase.com/platform/v2/x402"
BASE_MAINNET = "eip155:8453"
BASE_SEPOLIA = "eip155:84532"
PAID_ROUTE = "POST /v1/x402/pre-sign"
_EVM_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
_ledger_lock = threading.Lock()


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class X402Settings:
    enabled: bool = False
    network: str = BASE_MAINNET
    price: str = "$0.01"
    pay_to: str = ""
    resource_url: str = ""
    facilitator_url: str = CDP_FACILITATOR_URL
    cdp_api_key_id: str = ""
    cdp_api_key_secret: str = ""
    settlement_log: Path = Path("runtime/x402-settlements.jsonl")

    @classmethod
    def from_env(cls) -> "X402Settings":
        return cls(
            enabled=_enabled(os.getenv("RUGBUSTER_X402_ENABLED")),
            network=os.getenv("RUGBUSTER_X402_NETWORK", BASE_MAINNET).strip(),
            price=os.getenv("RUGBUSTER_X402_PRICE", "$0.01").strip(),
            pay_to=os.getenv("RUGBUSTER_X402_PAY_TO", "").strip(),
            resource_url=os.getenv("RUGBUSTER_X402_RESOURCE_URL", "").rstrip("/"),
            facilitator_url=os.getenv(
                "RUGBUSTER_X402_FACILITATOR_URL", CDP_FACILITATOR_URL
            ).rstrip("/"),
            cdp_api_key_id=os.getenv("CDP_API_KEY_ID", "").strip(),
            cdp_api_key_secret=os.getenv("CDP_API_KEY_SECRET", ""),
            settlement_log=Path(
                os.getenv("RUGBUSTER_X402_SETTLEMENT_LOG", "runtime/x402-settlements.jsonl")
            ),
        )

    def validate(self) -> None:
        if not self.enabled:
            return
        if self.network not in {BASE_MAINNET, BASE_SEPOLIA}:
            raise ValueError("RUGBUSTER_X402_NETWORK must be Base mainnet or Base Sepolia")
        if not _EVM_ADDRESS.fullmatch(self.pay_to):
            raise ValueError("RUGBUSTER_X402_PAY_TO must be an EVM address")
        if not re.fullmatch(r"\$\d+(?:\.\d{1,6})?", self.price):
            raise ValueError("RUGBUSTER_X402_PRICE must look like $0.01")
        parsed = urlsplit(self.resource_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("RUGBUSTER_X402_RESOURCE_URL must be a public HTTPS URL")
        if not self.cdp_api_key_id or not self.cdp_api_key_secret:
            raise ValueError("CDP_API_KEY_ID and CDP_API_KEY_SECRET are required")

    def public_status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "x402_version": 2,
            "route": PAID_ROUTE,
            "network": self.network,
            "price": self.price,
            "pay_to": self.pay_to if self.enabled else None,
            "resource_url": self.resource_url if self.enabled else None,
        }


class CdpAuthProvider:
    """Adapt Coinbase's official CDP x402 headers to the x402 SDK protocol."""

    def __init__(self, settings: X402Settings) -> None:
        self._create_headers = create_cdp_auth_headers(
            settings.cdp_api_key_id,
            settings.cdp_api_key_secret,
        )

    def get_auth_headers(self) -> AuthHeaders:
        headers = self._create_headers()
        return AuthHeaders(
            verify=headers["verify"],
            settle=headers["settle"],
            supported=headers["supported"],
            bazaar=headers["list"],
        )


class CdpFacilitatorClient(HTTPFacilitatorClient):
    """Declare the configured CDP rail without a fragile startup network call."""

    def __init__(self, config: FacilitatorConfig, network: str) -> None:
        super().__init__(config)
        self._network = network

    def get_supported(self) -> SupportedResponse:
        return SupportedResponse(
            kinds=[SupportedKind(x402_version=2, scheme="exact", network=self._network)]
        )


def _append_settlement(settings: X402Settings, context: Any) -> None:
    result = context.result
    response_headers = getattr(context.transport_context, "response_headers", {}) or {}
    record = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "x402_version": 2,
        "network": result.network,
        "transaction": result.transaction,
        "payer": result.payer,
        "amount": result.amount or context.requirements.amount,
        "asset": context.requirements.asset,
        "pay_to": context.requirements.pay_to,
        "route": PAID_ROUTE,
        "phase": context.phase,
        "decision_hash": response_headers.get("x-rugbuster-decision-hash"),
        "memory_evidence_hash": response_headers.get("x-rugbuster-memory-evidence-hash"),
    }
    path = settings.settlement_log
    path.parent.mkdir(parents=True, exist_ok=True)
    with _ledger_lock, path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def build_x402_server(settings: X402Settings) -> tuple[x402ResourceServer, HTTPFacilitatorClient]:
    settings.validate()
    facilitator = CdpFacilitatorClient(
        FacilitatorConfig(
            url=settings.facilitator_url,
            auth_provider=CdpAuthProvider(settings),
            identifier="coinbase-cdp",
        ),
        settings.network,
    )
    server = x402ResourceServer(facilitator)
    server.register(settings.network, ExactEvmServerScheme())
    server.on_after_settle(lambda context: _append_settlement(settings, context))
    return server, facilitator


def install_x402_middleware(
    app: FastAPI,
    settings: X402Settings,
    *,
    server: x402ResourceServer | None = None,
) -> HTTPFacilitatorClient | None:
    settings.validate()
    if not settings.enabled:
        return None

    facilitator: HTTPFacilitatorClient | None = None
    if server is None:
        server, facilitator = build_x402_server(settings)
    routes = {
        PAID_ROUTE: RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                pay_to=settings.pay_to,
                price=settings.price,
                network=settings.network,
            ),
            resource=f"{settings.resource_url}/v1/x402/pre-sign",
            mime_type="application/json",
            description=(
                "Memory-backed pre-sign verdict with deployer-history evidence and "
                "a decision hash suitable for a Base audit receipt."
            ),
            service_name="RugBuster Memory Firewall",
            tags=["security", "memory", "pre-sign", "Base"],
        )
    }
    app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)
    return facilitator
