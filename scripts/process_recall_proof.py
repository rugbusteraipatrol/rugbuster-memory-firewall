"""Re-query real evidence, then write and recall in separate OS processes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from sibyl_memory_client import MemoryClient
from rugbuster_memory_firewall import MemoryFirewall
from verify_real_case import recall_demo, verify_case

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("write", "read"))
    parser.add_argument("--db", type=Path)
    parser.add_argument("--verified", type=Path)
    args = parser.parse_args()
    case = json.loads((ROOT / "evidence/avax-repeat-deployer-case.json").read_text())
    print(f"utc={datetime.now(UTC).isoformat()} pid={os.getpid()} stage={args.stage or 'verify'}", flush=True)
    if args.stage == "write":
        if args.db.exists():
            raise RuntimeError("Writer requires an empty, new database path")
        recall_demo(case, json.loads(args.verified.read_text()), args.db)
        print("writer_complete=true", flush=True)
        return
    if args.stage == "read":
        if not args.db.is_file():
            raise RuntimeError("Persisted database missing; refusing to initialize it")
        memory = MemoryClient.local(str(args.db))
        try:
            decision = MemoryFirewall(memory).pre_sign(
                chain=case["chain"], token_address=case["recall_target"]["token_address"],
                deployer=case["deployer"], current_risk="clean",
                action={"type": "process-recall-demo", "executes_transaction": False},
                session_id="separate-process-recall",
            )
        finally:
            memory._storage.close()
        if decision.verdict != "BLOCK" or decision.evidence_count != 2:
            raise RuntimeError("Separate-process recall failed")
        print(json.dumps({"verdict": decision.verdict, "evidence_count": decision.evidence_count,
                          "memory_evidence_hash": decision.memory_evidence_hash,
                          "reason_codes": decision.reason_codes}), flush=True)
        print(f"database_file_bytes={args.db.stat().st_size}", flush=True)
        print("separate_process_recall=PASSED", flush=True)
        return
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    print(f"commit={commit} working_tree_dirty={str(dirty).lower()} current_risk=controlled_clean_input", flush=True)
    verified = verify_case(case)
    with tempfile.TemporaryDirectory(prefix="rugbuster-process-proof-") as directory:
        db = Path(directory) / "memory.db"
        observations = Path(directory) / "verified.json"
        observations.write_text(json.dumps(verified))
        for stage in ("write", "read"):
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--stage", stage,
                            "--db", str(db), "--verified", str(observations)], cwd=ROOT, check=True)
        result = MemoryFirewall(None).pre_sign(
            chain=case["chain"], token_address=case["recall_target"]["token_address"],
            deployer=case["deployer"], current_risk="clean", action={"type": "demo"},
            session_id="disabled-memory",
        )
        if result.verdict != "MEMORY_REQUIRED":
            raise RuntimeError("Memory-disabled gate failed")
        print("memory_access_disabled=PASSED verdict=MEMORY_REQUIRED", flush=True)


if __name__ == "__main__":
    main()
