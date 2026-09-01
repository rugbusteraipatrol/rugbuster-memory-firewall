"""Developer smoke test for fresh-session recall using explicit fixtures.

This is not the final hackathon demo. The submission demo must use a real,
publicly verifiable repeat-deployer case.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sibyl_memory_client import MemoryClient

from rugbuster_memory_firewall import MemoryFirewall, VerifiedObservation


def close(memory: MemoryClient) -> None:
    memory._storage.close()  # type: ignore[attr-defined]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("demo-memory.db"))
    args = parser.parse_args()

    writer = MemoryClient.local(args.db)
    firewall = MemoryFirewall(writer)
    before = firewall.pre_sign(
        chain="avax",
        deployer="0xDemoDeployer",
        current_risk="clean",
        session_id="fixture-before",
    )
    firewall.record_observation(
        chain="avax",
        deployer="0xDemoDeployer",
        observation=VerifiedObservation.now(
            kind="critical",
            source="developer-test-fixture",
            evidence_uri="fixture://critical-observation",
            details="Synthetic evidence used only to verify persistence.",
        ),
    )
    close(writer)

    # A new MemoryClient proves the second result is persisted recall, not RAM.
    fresh_client = MemoryClient.local(args.db)
    after = MemoryFirewall(fresh_client).pre_sign(
        chain="avax",
        deployer="0xDemoDeployer",
        current_risk="clean",
        session_id="fixture-after",
    )
    close(fresh_client)

    print("fixture_only=true")
    print(f"before={before.verdict}")
    print("fresh_session=true")
    print(f"after={after.verdict}")
    print(f"reason_code={after.reason_codes[0]}")
    print(f"evidence_count={after.evidence_count}")


if __name__ == "__main__":
    main()
