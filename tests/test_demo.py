from typing import Any

from fastapi.testclient import TestClient

from rugbuster_memory_firewall import demo


def test_summary_exposes_real_case() -> None:
    response = TestClient(demo.create_demo_app()).get("/api/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == "avax-repeat-deployer-2026-06-23"
    assert len(payload["historical_events"]) == 2
    assert payload["receipt"]["verdict"] == "BLOCK"


def test_deletion_demo_fails_closed() -> None:
    response = TestClient(demo.create_demo_app()).post("/api/proof/deletion")

    assert response.status_code == 200
    assert response.json()["status"] == "passed"
    assert response.json()["verdict"] == "MEMORY_REQUIRED"


def test_base_proof_decodes_and_matches(monkeypatch: Any) -> None:
    expected = demo._load_json("base-sepolia-decision-receipt.json")
    memory = expected["memory_evidence_hash"].removeprefix("0x")
    recorded_at = f'{expected["recorded_at"]:064x}'
    offset = f"{96:064x}"
    policy = expected["policy_version"].encode().hex()
    dynamic = f"{len(expected['policy_version']):064x}" + policy.ljust(64, "0")
    event_log = {
        "address": expected["contract_address"],
        "topics": [
            "0xevent-signature",
            expected["decision_hash"],
            "0x" + expected["submitter"].removeprefix("0x").rjust(64, "0"),
            "0x" + f'{expected["verdict_value"]:064x}',
        ],
        "data": "0x" + memory + recorded_at + offset + dynamic,
    }

    def fake_rpc(method: str, _params: list[Any]) -> dict[str, Any]:
        if method == "eth_getTransactionByHash":
            return {"hash": expected["transaction_hash"]}
        return {"status": "0x1", "logs": [event_log]}

    monkeypatch.setattr(demo, "_rpc", fake_rpc)
    response = TestClient(demo.create_demo_app()).post("/api/proof/base")

    assert response.status_code == 200
    assert response.json()["status"] == "verified"
    assert all(response.json()["checks"].values())
