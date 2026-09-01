"""Verified AVAX and Solana deployer resolution adapters."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

AVAX_CREATION_API = (
    "https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api"
)
RUGCHECK_REPORT_API = "https://api.rugcheck.xyz/v1/tokens/{token}/report"

_EVM_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
_SOLANA_ADDRESS = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class ResolutionError(RuntimeError):
    """Raised when a deployer cannot be resolved and verified."""


class JsonTransport(Protocol):
    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]: ...


class HttpxJsonTransport:
    def __init__(self, *, timeout_seconds: float = 12.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = httpx.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
                follow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ResolutionError(f"deployer provider failed: {error.__class__.__name__}") from error
        if not isinstance(payload, dict):
            raise ResolutionError("deployer provider returned a non-object response")
        return payload


@dataclass(frozen=True)
class ResolvedDeployer:
    chain: str
    token_address: str
    deployer_address: str
    source: str
    evidence_uri: str
    creation_tx_hash: str | None
    resolved_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "token_address": self.token_address,
            "deployer_address": self.deployer_address,
            "source": self.source,
            "evidence_uri": self.evidence_uri,
            "creation_tx_hash": self.creation_tx_hash,
            "resolved_at": self.resolved_at,
        }


class DeployerResolver:
    def __init__(self, transport: JsonTransport | None = None) -> None:
        self.transport = transport or HttpxJsonTransport()

    def resolve(self, *, chain: str, token_address: str) -> ResolvedDeployer:
        normalized_chain = chain.strip().lower()
        if normalized_chain in {"avax", "avalanche"}:
            return self._resolve_avax(token_address)
        if normalized_chain == "solana":
            return self._resolve_solana(token_address)
        raise ResolutionError(f"unsupported chain: {chain}")

    def _resolve_avax(self, token_address: str) -> ResolvedDeployer:
        token = token_address.strip()
        if not _EVM_ADDRESS.fullmatch(token):
            raise ResolutionError("invalid Avalanche contract address")
        headers = {"Accept": "application/json"}
        api_key = os.getenv("ROUTESCAN_API_KEY", "").strip()
        if api_key:
            headers["apikey"] = api_key
        payload = self.transport.get_json(
            AVAX_CREATION_API,
            params={
                "module": "contract",
                "action": "getcontractcreation",
                "contractaddresses": token,
            },
            headers=headers,
        )
        if payload.get("status") not in (None, "1", 1):
            raise ResolutionError("Routescan reported an unsuccessful lookup")
        result = payload.get("result")
        if not isinstance(result, list) or not result or not isinstance(result[0], dict):
            raise ResolutionError("Routescan returned no contract creation record")
        record = result[0]
        returned_contract = str(record.get("contractAddress", ""))
        creator = str(record.get("contractCreator", ""))
        tx_hash = str(record.get("txHash", ""))
        if returned_contract.lower() != token.lower() or not _EVM_ADDRESS.fullmatch(creator):
            raise ResolutionError("Routescan contract creation record failed validation")
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash):
            raise ResolutionError("Routescan returned an invalid creation transaction hash")
        return ResolvedDeployer(
            chain="avax",
            token_address=token.lower(),
            deployer_address=creator.lower(),
            source="routescan_contract_creation",
            evidence_uri=f"https://snowtrace.io/tx/{tx_hash}",
            creation_tx_hash=tx_hash.lower(),
            resolved_at=datetime.now(UTC).isoformat(),
        )

    def _resolve_solana(self, token_address: str) -> ResolvedDeployer:
        token = token_address.strip()
        if not _SOLANA_ADDRESS.fullmatch(token):
            raise ResolutionError("invalid Solana mint address")
        endpoint = RUGCHECK_REPORT_API.format(token=token)
        payload = self.transport.get_json(endpoint, headers={"Accept": "application/json"})
        creator = str(payload.get("creator") or payload.get("deployer") or "")
        if not _SOLANA_ADDRESS.fullmatch(creator):
            raise ResolutionError("RugCheck returned no valid creator address")
        return ResolvedDeployer(
            chain="solana",
            token_address=token,
            deployer_address=creator,
            source="rugcheck_full_report",
            evidence_uri=endpoint,
            creation_tx_hash=None,
            resolved_at=datetime.now(UTC).isoformat(),
        )


def same_deployer(chain: str, supplied: str, resolved: str) -> bool:
    if chain.strip().lower() in {"avax", "avalanche"}:
        return supplied.strip().lower() == resolved.strip().lower()
    return supplied.strip() == resolved.strip()
