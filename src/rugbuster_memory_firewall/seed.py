"""Seed a production memory database from a committed verified-case artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient

from .firewall import MemoryFirewall, VerifiedObservation


def seed_verified_case(memory: MemoryClient, artifact_path: Path) -> int:
    case: dict[str, Any] = json.loads(artifact_path.read_text(encoding="utf-8"))
    firewall = MemoryFirewall(memory)
    explorer = case["source_endpoints"]["explorer_tx_prefix"]
    seeded = 0

    for event in case["historical_events"]:
        returned = event["liquidity_return"]
        added = event["liquidity_add"]
        elapsed = returned["timestamp"] - added["timestamp"]
        details = (
            f"Public chain data shows {added['wavax_wei']} wei WAVAX sent from the "
            f"creator to pool {event['pool_address']} and {returned['wavax_wei']} wei "
            f"returned to the creator {elapsed} seconds later."
        )
        firewall.record_observation(
            chain=case["chain"],
            deployer=case["deployer"],
            observation=VerifiedObservation.at(
                kind="critical",
                source="Avalanche C-Chain public data (Routescan + public RPC)",
                evidence_uri=explorer + returned["tx"],
                details=details,
                observed_at=datetime.fromtimestamp(returned["timestamp"], UTC).isoformat(),
            ),
        )
        seeded += 1
    return seeded
