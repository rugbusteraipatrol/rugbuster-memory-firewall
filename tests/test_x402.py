import base64
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sibyl_memory_client import MemoryClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import SettleResponse, SupportedResponse, VerifyResponse
from x402.schemas.responses import SupportedKind
from x402.server import x402ResourceServer

from rugbuster_memory_firewall.api import create_app
from rugbuster_memory_firewall.resolver import ResolvedDeployer
from rugbuster_memory_firewall.x402 import BASE_MAINNET, X402Settings, _append_settlement

pytestmark = pytest.mark.anyio
PAY_TO = "0x" + "4" * 40
AVAX_TOKEN = "0x" + "1" * 40
AVAX_DEPLOYER = "0x" + "2" * 40


class FakeResolver:
    def resolve(self, *, chain: str, token_address: str) -> ResolvedDeployer:
        return ResolvedDeployer(
            chain="avax",
            token_address=token_address.lower(),
            deployer_address=AVAX_DEPLOYER,
            source="test_contract_creation",
            evidence_uri="https://example.test/tx/creation",
            creation_tx_hash="0x" + "a" * 64,
            resolved_at="2026-09-01T00:00:00+00:00",
        )


def _payload() -> dict[str, object]:
    return {
        "chain": "avax",
        "token_address": AVAX_TOKEN,
        "deployer_address": AVAX_DEPLOYER,
        "current_risk": "clean",
        "action": {"type": "swap", "amount": "1.0"},
        "session_id": "x402-test",
    }


class FakeFacilitator:
    def get_supported(self) -> SupportedResponse:
        return SupportedResponse(
            kinds=[SupportedKind(x402_version=2, scheme="exact", network=BASE_MAINNET)]
        )

    async def verify(self, *_args: object, **_kwargs: object) -> VerifyResponse:
        raise AssertionError("an unpaid request must not be verified")

    async def settle(self, *_args: object, **_kwargs: object) -> SettleResponse:
        raise AssertionError("an unpaid request must not be settled")


def _settings(tmp_path: Path, *, enabled: bool = True) -> X402Settings:
    return X402Settings(
        enabled=enabled,
        network=BASE_MAINNET,
        price="$0.01",
        pay_to=PAY_TO,
        resource_url="https://firewall.example.test",
        cdp_api_key_id="organizations/test/apiKeys/test",
        cdp_api_key_secret="test-secret",
        settlement_log=tmp_path / "settlements.jsonl",
    )


def _server() -> x402ResourceServer:
    server = x402ResourceServer(FakeFacilitator())  # type: ignore[arg-type]
    server.register(BASE_MAINNET, ExactEvmServerScheme())
    return server


async def test_paid_route_returns_real_x402_challenge_without_payment(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    app = create_app(
        memory=memory,
        resolver=FakeResolver(),  # type: ignore[arg-type]
        x402_settings=_settings(tmp_path),
        x402_server=_server(),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://firewall.example.test"
    ) as client:
        response = await client.post("/v1/x402/pre-sign", json=_payload())
    memory._storage.close()  # type: ignore[attr-defined]

    assert response.status_code == 402
    assert "payment-required" in response.headers
    challenge = json.loads(base64.b64decode(response.headers["payment-required"]))
    assert challenge["x402Version"] == 2
    assert challenge["accepts"][0]["network"] == BASE_MAINNET
    assert challenge["accepts"][0]["payTo"] == PAY_TO


async def test_disabled_paid_route_fails_closed(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    app = create_app(
        memory=memory,
        resolver=FakeResolver(),  # type: ignore[arg-type]
        x402_settings=_settings(tmp_path, enabled=False),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/v1/x402/pre-sign", json=_payload())
        status = await client.get("/.well-known/x402")
    memory._storage.close()  # type: ignore[attr-defined]

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "X402_NOT_ENABLED"
    assert status.json()["enabled"] is False


def test_enabled_configuration_rejects_non_public_resource_url(tmp_path: Path) -> None:
    settings = X402Settings(
        **{
            **_settings(tmp_path).__dict__,
            "resource_url": "http://127.0.0.1:8765",
        }
    )
    with pytest.raises(ValueError, match="public HTTPS"):
        settings.validate()


def test_settlement_log_binds_payment_to_decision_and_memory(tmp_path: Path) -> None:
    @dataclass
    class Requirements:
        amount: str = "10000"
        asset: str = "0x" + "8" * 40
        pay_to: str = PAY_TO

    context = SimpleNamespace(
        result=SettleResponse(
            success=True,
            payer="0x" + "9" * 40,
            transaction="0x" + "a" * 64,
            network=BASE_MAINNET,
            amount="10000",
        ),
        requirements=Requirements(),
        phase="after-handler",
        transport_context=SimpleNamespace(
            response_headers={
                "x-rugbuster-decision-hash": "0x" + "b" * 64,
                "x-rugbuster-memory-evidence-hash": "0x" + "c" * 64,
            }
        ),
    )

    settings = _settings(tmp_path)
    _append_settlement(settings, context)
    record = json.loads(settings.settlement_log.read_text(encoding="utf-8"))

    assert record["transaction"] == "0x" + "a" * 64
    assert record["decision_hash"] == "0x" + "b" * 64
    assert record["memory_evidence_hash"] == "0x" + "c" * 64
    assert "payment_signature" not in record
