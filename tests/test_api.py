from pathlib import Path

import httpx
import pytest
from sibyl_memory_client import MemoryClient

from rugbuster_memory_firewall import (
    MemoryFirewall,
    ResolutionError,
    ResolvedDeployer,
    VerifiedObservation,
)
from rugbuster_memory_firewall.api import create_app

AVAX_TOKEN = "0x" + "1" * 40
AVAX_DEPLOYER = "0x" + "2" * 40
pytestmark = pytest.mark.anyio


class FakeResolver:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def resolve(self, *, chain: str, token_address: str) -> ResolvedDeployer:
        if self.fail:
            raise ResolutionError("provider unavailable")
        return ResolvedDeployer(
            chain="avax",
            token_address=token_address.lower(),
            deployer_address=AVAX_DEPLOYER,
            source="test_contract_creation",
            evidence_uri="https://example.test/tx/creation",
            creation_tx_hash="0x" + "a" * 64,
            resolved_at="2026-09-01T00:00:00+00:00",
        )


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "chain": "avax",
        "token_address": AVAX_TOKEN,
        "deployer_address": AVAX_DEPLOYER,
        "current_risk": "clean",
        "action": {"type": "swap", "amount": "1.0"},
        "session_id": "api-test",
    }
    payload.update(overrides)
    return payload


def _close(memory: MemoryClient) -> None:
    memory._storage.close()  # type: ignore[attr-defined]


def _client(app: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    )


async def test_api_returns_action_bound_allow_decision(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    async with _client(create_app(memory=memory, resolver=FakeResolver())) as client:  # type: ignore[arg-type]
        response = await client.post("/v1/pre-sign", json=_payload())
    _close(memory)

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "ALLOW"
    assert body["reason_codes"] == ["ALLOW_CLEAN_CURRENT_AND_HISTORY"]
    assert body["action_hash"].startswith("0x")
    assert body["decision_hash"].startswith("0x")
    assert body["resolver_source"] == "test_contract_creation"


async def test_api_returns_recalled_history_and_block(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    MemoryFirewall(memory).record_observation(
        chain="avax",
        deployer=AVAX_DEPLOYER,
        observation=VerifiedObservation.now(
            kind="critical",
            source="independent-test-source",
            evidence_uri="https://evidence.test/critical",
            details="Verified fixture for API integration test.",
        ),
    )
    async with _client(create_app(memory=memory, resolver=FakeResolver())) as client:  # type: ignore[arg-type]
        response = await client.post(
            "/v1/pre-sign", json=_payload(session_id="blocked-api-test")
        )
    _close(memory)

    body = response.json()
    assert response.status_code == 200
    assert body["verdict"] == "BLOCK"
    assert body["reason_codes"] == ["BLOCK_REPEAT_DEPLOYER"]
    assert body["history"][0]["evidence_uri"] == "https://evidence.test/critical"
    assert "https://evidence.test/critical" in body["evidence_sources"]


async def test_api_rejects_supplied_deployer_mismatch(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    async with _client(create_app(memory=memory, resolver=FakeResolver())) as client:  # type: ignore[arg-type]
        response = await client.post(
            "/v1/pre-sign",
            json=_payload(deployer_address="0x" + "3" * 40),
        )
    _close(memory)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DEPLOYER_MISMATCH"


async def test_api_fails_closed_when_resolver_is_unavailable(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    async with _client(
        create_app(memory=memory, resolver=FakeResolver(fail=True))  # type: ignore[arg-type]
    ) as client:
        response = await client.post("/v1/pre-sign", json=_payload())
    _close(memory)

    assert response.status_code == 424
    assert response.json()["detail"]["code"] == "DEPLOYER_UNRESOLVED"


async def test_api_exposes_memory_required_when_memory_fails() -> None:
    class UnavailableMemory:
        def set_reference(self, *_args: object, **_kwargs: object) -> None:
            raise OSError("memory unavailable")

    async with _client(
        create_app(memory=UnavailableMemory(), resolver=FakeResolver())  # type: ignore[arg-type]
    ) as client:
        response = await client.post("/v1/pre-sign", json=_payload())

    assert response.status_code == 200
    assert response.json()["verdict"] == "MEMORY_REQUIRED"


async def test_health_declares_memory_required(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    async with _client(create_app(memory=memory, resolver=FakeResolver())) as client:  # type: ignore[arg-type]
        response = await client.get("/health")
    _close(memory)

    assert response.json() == {"status": "ok", "memory_policy": "required"}

