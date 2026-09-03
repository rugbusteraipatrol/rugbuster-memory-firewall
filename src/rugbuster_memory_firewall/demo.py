"""Judge-facing demo console backed by the real verification paths."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .firewall import MemoryFirewall

ROOT = Path(os.getenv("RUGBUSTER_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
STATIC = Path(__file__).with_name("static")
EVIDENCE = ROOT / "evidence"
BASE_RPC = "https://sepolia.base.org"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def _decode_decision_event(log: dict[str, Any]) -> dict[str, Any]:
    topics = log.get("topics", [])
    raw = str(log.get("data", "")).removeprefix("0x")
    if len(topics) != 4 or len(raw) < 64 * 4:
        raise ValueError("DecisionRecorded event is malformed")
    memory_hash = "0x" + raw[0:64]
    recorded_at = int(raw[64:128], 16)
    string_offset = int(raw[128:192], 16) * 2
    policy_length = int(raw[string_offset : string_offset + 64], 16)
    length_start = string_offset
    value_start = length_start + 64
    policy_hex = raw[value_start : value_start + policy_length * 2]
    return {
        "decision_hash": topics[1],
        "submitter": "0x" + topics[2][-40:],
        "memory_evidence_hash": memory_hash,
        "verdict_value": int(topics[3], 16),
        "recorded_at": recorded_at,
        "policy_version": bytes.fromhex(policy_hex).decode("utf-8"),
    }


def _rpc(method: str, params: list[Any]) -> Any:
    response = httpx.post(
        BASE_RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"].get("message", "Base RPC error"))
    return payload.get("result")


def create_demo_app() -> FastAPI:
    app = FastAPI(title="RugBuster Judge Console", version="0.1.0")
    app.mount("/assets", StaticFiles(directory=STATIC), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/api/summary")
    def summary() -> dict[str, Any]:
        case = _load_json("avax-repeat-deployer-case.json")
        receipt = _load_json("base-sepolia-decision-receipt.json")
        return {
            "case_id": case["case_id"],
            "chain": case["chain"],
            "deployer": case["deployer"],
            "historical_events": case["historical_events"],
            "recall_target": case["recall_target"],
            "policy": case["policy"],
            "receipt": receipt,
        }

    @app.post("/api/proof/live")
    def live_proof() -> dict[str, Any]:
        try:
            result = subprocess.run(
                [sys.executable, "scripts/verify_real_case.py"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                timeout=45,
            )
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            decision_line = next(
                line for line in lines if line.startswith("fresh_session_decision=")
            )
            decision = json.loads(decision_line.split("=", 1)[1])
        except (subprocess.SubprocessError, StopIteration, json.JSONDecodeError) as error:
            raise HTTPException(status_code=502, detail="Live proof did not complete") from error
        return {
            "status": "verified",
            "observations": [line for line in lines if line.startswith("verified token=")],
            "decision": decision,
        }

    @app.post("/api/proof/deletion")
    def deletion_proof() -> dict[str, Any]:
        decision = MemoryFirewall(None).pre_sign(
            chain="avax",
            token_address="0xb369f24c85e14f1fe4803114b8b1ed44b83d19c2",
            deployer="0x1f6908b79ae1f2c87c16f0facc9084d93601c8eb",
            current_risk="clean",
            action={"type": "pre_sign_demo"},
            session_id="memory-deleted",
        )
        return {
            "status": "passed" if decision.verdict == "MEMORY_REQUIRED" else "failed",
            "verdict": decision.verdict,
            "reason_codes": decision.reason_codes,
        }

    @app.post("/api/proof/base")
    def base_proof() -> dict[str, Any]:
        expected = _load_json("base-sepolia-decision-receipt.json")
        try:
            transaction = _rpc("eth_getTransactionByHash", [expected["transaction_hash"]])
            receipt = _rpc("eth_getTransactionReceipt", [expected["transaction_hash"]])
            if transaction is None or receipt is None:
                raise RuntimeError("Base transaction was not found")
            contract_log = next(
                log
                for log in receipt["logs"]
                if log["address"].lower() == expected["contract_address"].lower()
            )
            decoded = _decode_decision_event(contract_log)
            checks = {
                "transaction_success": int(receipt["status"], 16) == 1,
                "contract_event_found": contract_log["address"].lower()
                == expected["contract_address"].lower(),
                "decision_hash_matches": decoded["decision_hash"].lower()
                == expected["decision_hash"].lower(),
                "memory_hash_matches": decoded["memory_evidence_hash"].lower()
                == expected["memory_evidence_hash"].lower(),
                "verdict_matches": decoded["verdict_value"] == expected["verdict_value"],
                "policy_matches": decoded["policy_version"] == expected["policy_version"],
                "submitter_matches": decoded["submitter"].lower()
                == expected["submitter"].lower(),
            }
        except (httpx.HTTPError, KeyError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=502, detail="Base proof did not complete") from error
        return {
            "status": "verified" if all(checks.values()) else "mismatch",
            "checks": checks,
            "decoded": decoded,
            "explorer_tx": expected["explorer_tx"],
        }

    return app


app = create_demo_app()
