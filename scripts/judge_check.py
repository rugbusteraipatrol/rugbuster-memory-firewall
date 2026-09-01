"""Run the deterministic judge checks, with an optional live evidence pass."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from rugbuster_memory_firewall import MemoryFirewall

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str]) -> None:
    print(f"\n=== {label} ===", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def verify_deletion_gate() -> None:
    decision = MemoryFirewall(None).pre_sign(
        chain="avax",
        token_address="0x0000000000000000000000000000000000000001",
        deployer="0x0000000000000000000000000000000000000002",
        current_risk="clean",
        action={"type": "judge_check"},
        session_id="memory-deleted",
    )
    if decision.verdict != "MEMORY_REQUIRED":
        raise RuntimeError(f"deletion gate failed with {decision.verdict}")
    print(f"deletion_gate=PASSED verdict={decision.verdict}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="also re-query public Avalanche evidence and run fresh-session recall",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    npm_name = "npm.cmd" if sys.platform == "win32" else "npm"
    npm = shutil.which(npm_name)
    if npm is None:
        raise RuntimeError("npm is required but was not found on PATH")
    run("Python tests", [sys.executable, "-m", "pytest"])
    run("Base contract tests", [npm, "run", "base:test"])
    verify_deletion_gate()
    if args.live:
        run("Live Avalanche and fresh-session proof", [sys.executable, "scripts/verify_real_case.py"])
    print("\njudge_check=PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
