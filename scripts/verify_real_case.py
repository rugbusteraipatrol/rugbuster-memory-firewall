"""Re-verify the public AVAX case and exercise fresh-session Sibyl recall."""

from __future__ import annotations

import argparse
import json
import tempfile
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient

from rugbuster_memory_firewall import MemoryFirewall, VerifiedObservation


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read())


def _routescan(endpoint: str, **params: str) -> list[dict[str, Any]]:
    url = f"{endpoint}?{urllib.parse.urlencode(params)}"
    payload = _get_json(url)
    result = payload.get("result")
    if not isinstance(result, list):
        raise RuntimeError(f"Routescan returned an invalid result for {params['action']}")
    return result


def _rpc(endpoint: str, method: str, params: list[Any]) -> Any:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode()
    request = urllib.request.Request(
        endpoint, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read())
    if "error" in payload:
        raise RuntimeError(f"RPC error: {payload['error']}")
    return payload["result"]


def _same(left: str, right: str) -> bool:
    return left.lower() == right.lower()


def _receipt_ok(rpc: str, tx_hash: str, contract: str | None = None) -> None:
    receipt = _rpc(rpc, "eth_getTransactionReceipt", [tx_hash])
    if receipt is None or receipt.get("status") != "0x1":
        raise AssertionError(f"transaction did not succeed: {tx_hash}")
    if contract and not _same(receipt.get("contractAddress") or "", contract):
        raise AssertionError(f"creation receipt does not contain {contract}")


def verify_case(case: dict[str, Any]) -> list[dict[str, Any]]:
    endpoints = case["source_endpoints"]
    routescan = endpoints["routescan"]
    rpc = endpoints["avalanche_rpc"]
    deployer = case["deployer"]
    wavax = case["wavax_contract"]

    if _rpc(rpc, "eth_chainId", []) != hex(case["chain_id"]):
        raise AssertionError("RPC chain ID does not match the case")
    if _rpc(rpc, "eth_getCode", [deployer, "latest"]) != "0x":
        raise AssertionError("deployer is a contract, not an externally owned account")

    verified = []
    for event in case["historical_events"]:
        token = event["token_address"]
        creation = _routescan(
            routescan,
            module="contract",
            action="getcontractcreation",
            contractaddresses=token,
        )[0]
        if not _same(creation["contractCreator"], deployer):
            raise AssertionError(f"creator mismatch for {token}")
        if not _same(creation["txHash"], event["creation_tx"]):
            raise AssertionError(f"creation transaction mismatch for {token}")

        token_transfers = _routescan(
            routescan,
            module="account",
            action="tokentx",
            contractaddress=token,
            page="1",
            offset="10",
            sort="asc",
        )
        if not any(
            _same(item["from"], deployer) and _same(item["to"], event["pool_address"])
            for item in token_transfers
        ):
            raise AssertionError(f"deployer-to-pool token transfer missing for {token}")

        flow = _routescan(
            routescan,
            module="account",
            action="tokentx",
            contractaddress=wavax,
            address=event["pool_address"],
            page="1",
            offset="10",
            sort="asc",
        )
        add = event["liquidity_add"]
        returned = event["liquidity_return"]
        add_match = next((item for item in flow if _same(item["hash"], add["tx"])), None)
        return_match = next(
            (item for item in flow if _same(item["hash"], returned["tx"])), None
        )
        if not add_match or not return_match:
            raise AssertionError(f"expected WAVAX transfers missing for {token}")
        if not (_same(add_match["from"], deployer) and _same(add_match["to"], event["pool_address"])):
            raise AssertionError(f"invalid liquidity-add direction for {token}")
        if not (
            _same(return_match["from"], event["pool_address"])
            and _same(return_match["to"], deployer)
        ):
            raise AssertionError(f"invalid liquidity-return direction for {token}")

        actual_add = int(add_match["value"])
        actual_return = int(return_match["value"])
        add_timestamp = int(add_match["timeStamp"])
        return_timestamp = int(return_match["timeStamp"])
        if actual_add != int(add["wavax_wei"]) or actual_return != int(returned["wavax_wei"]):
            raise AssertionError(f"WAVAX amount mismatch for {token}")
        if add_timestamp != add["timestamp"] or return_timestamp != returned["timestamp"]:
            raise AssertionError(f"timestamp mismatch for {token}")

        elapsed = return_timestamp - add_timestamp
        ratio = actual_return / actual_add
        if elapsed > case["policy"]["maximum_elapsed_seconds"]:
            raise AssertionError(f"liquidity return was too slow for {token}")
        if ratio < case["policy"]["minimum_return_ratio"]:
            raise AssertionError(f"liquidity return ratio was too low for {token}")

        _receipt_ok(rpc, event["creation_tx"], token)
        _receipt_ok(rpc, add["tx"])
        _receipt_ok(rpc, returned["tx"])
        verified.append({"event": event, "elapsed": elapsed, "ratio": ratio})

    target = case["recall_target"]
    target_creation = _routescan(
        routescan,
        module="contract",
        action="getcontractcreation",
        contractaddresses=target["token_address"],
    )[0]
    if not _same(target_creation["contractCreator"], deployer):
        raise AssertionError("recall target has a different creator")
    if not _same(target_creation["txHash"], target["creation_tx"]):
        raise AssertionError("recall target creation transaction mismatch")
    _receipt_ok(rpc, target["creation_tx"], target["token_address"])
    return verified


def _close(memory: MemoryClient) -> None:
    memory._storage.close()  # type: ignore[attr-defined]


def recall_demo(case: dict[str, Any], verified: list[dict[str, Any]], db_path: Path) -> None:
    memory = MemoryClient.local(str(db_path))
    firewall = MemoryFirewall(memory)
    explorer = case["source_endpoints"]["explorer_tx_prefix"]
    for item in verified:
        event = item["event"]
        observed_at = datetime.fromtimestamp(
            event["liquidity_return"]["timestamp"], UTC
        ).isoformat()
        details = (
            f"Public chain data shows {event['liquidity_add']['wavax_wei']} wei WAVAX "
            f"sent from the creator to pool {event['pool_address']} and "
            f"{event['liquidity_return']['wavax_wei']} wei returned to the creator "
            f"{item['elapsed']} seconds later."
        )
        firewall.record_observation(
            chain=case["chain"],
            deployer=case["deployer"],
            observation=VerifiedObservation.at(
                kind="critical",
                source="Avalanche C-Chain public data (Routescan + public RPC)",
                evidence_uri=explorer + event["liquidity_return"]["tx"],
                details=details,
                observed_at=observed_at,
            ),
        )
    _close(memory)

    fresh_memory = MemoryClient.local(str(db_path))
    target = case["recall_target"]
    decision = MemoryFirewall(fresh_memory).pre_sign(
        chain=case["chain"],
        token_address=target["token_address"],
        deployer=case["deployer"],
        current_risk="clean",
        action={"type": "swap", "asset": target["token_address"], "demo": True},
        session_id="real-case-fresh-session",
    )
    _close(fresh_memory)
    print(
        "fresh_session_decision="
        + json.dumps(
            {
                "verdict": decision.verdict,
                "reason_codes": decision.reason_codes,
                "evidence_count": decision.evidence_count,
                "decision_hash": decision.decision_hash,
            },
            separators=(",", ":"),
        )
    )
    if decision.verdict != "BLOCK" or decision.reason_codes != ("BLOCK_REPEAT_DEPLOYER",):
        raise AssertionError("fresh-session recall did not block the repeated deployer")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        type=Path,
        default=Path("evidence/avax-repeat-deployer-case.json"),
    )
    parser.add_argument("--db", type=Path, help="Keep demo memory at this path")
    args = parser.parse_args()
    case = json.loads(args.case.read_text(encoding="utf-8"))
    verified = verify_case(case)
    for item in verified:
        event = item["event"]
        print(
            f"verified token={event['token_address']} creator={case['deployer']} "
            f"elapsed={item['elapsed']}s returned={item['ratio']:.6%}"
        )

    if args.db:
        args.db.parent.mkdir(parents=True, exist_ok=True)
        recall_demo(case, verified, args.db)
        print(f"memory_db={args.db} bytes={args.db.stat().st_size}")
    else:
        with tempfile.TemporaryDirectory(prefix="rugbuster-real-case-") as directory:
            recall_demo(case, verified, Path(directory) / "memory.db")


if __name__ == "__main__":
    main()
