from pathlib import Path

from sibyl_memory_client import MemoryClient

from rugbuster_memory_firewall import MemoryFirewall, VerifiedObservation


def _close(memory: MemoryClient) -> None:
    # MemoryClient 0.7.0 does not expose a public close method.
    memory._storage.close()  # type: ignore[attr-defined]


def _observation(kind: str, evidence: str) -> VerifiedObservation:
    return VerifiedObservation.now(
        kind=kind,  # type: ignore[arg-type]
        source="deterministic-test-fixture",
        evidence_uri=f"fixture://{evidence}",
        details=f"Verified test observation {evidence}.",
    )


def _decision(
    firewall: MemoryFirewall,
    *,
    chain: str,
    deployer: str,
    session_id: str,
):
    return firewall.pre_sign(
        chain=chain,
        token_address=f"fixture-token-{session_id}",
        deployer=deployer,
        current_risk="clean",
        action={"type": "test_action", "session": session_id},
        session_id=session_id,
    )


def test_entity_recall_survives_fresh_client(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    writer = MemoryClient.local(str(db_path))
    writer.set_entity("deployer", "demo-address", {"risk_events": 1})
    _close(writer)

    reader = MemoryClient.local(str(db_path))
    recalled = reader.get_entity("deployer", "demo-address")
    _close(reader)

    assert recalled is not None
    assert recalled["body"]["risk_events"] == 1


def test_fresh_session_recall_changes_decision(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    writer = MemoryClient.local(str(db_path))
    firewall = MemoryFirewall(writer)
    before = _decision(firewall, chain="avax", deployer="0xAbC", session_id="before")
    firewall.record_observation(
        chain="avax", deployer="0xAbC", observation=_observation("critical", "critical-1")
    )
    _close(writer)

    fresh_client = MemoryClient.local(str(db_path))
    after = _decision(
        MemoryFirewall(fresh_client), chain="avax", deployer="0xabc", session_id="after"
    )
    _close(fresh_client)

    assert before.verdict == "ALLOW"
    assert after.verdict == "BLOCK"
    assert after.reason_codes == ("BLOCK_REPEAT_DEPLOYER",)
    assert after.evidence_count == 1
    assert after.memory_evidence_hash is not None


def test_two_distinct_warnings_produce_warn(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    firewall = MemoryFirewall(memory)
    firewall.record_observation(
        chain="solana", deployer="DemoCreator", observation=_observation("warning", "warning-1")
    )
    firewall.record_observation(
        chain="solana", deployer="DemoCreator", observation=_observation("warning", "warning-2")
    )
    decision = _decision(
        firewall, chain="solana", deployer="DemoCreator", session_id="warnings"
    )
    _close(memory)

    assert decision.verdict == "WARN"
    assert decision.reason_codes == ("WARN_REPEATED_PATTERN",)


def test_duplicate_warning_does_not_inflate_history(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    firewall = MemoryFirewall(memory)
    warning = _observation("warning", "same-warning")
    firewall.record_observation(chain="avax", deployer="0x1", observation=warning)
    firewall.record_observation(chain="avax", deployer="0x1", observation=warning)
    decision = _decision(firewall, chain="avax", deployer="0x1", session_id="dedupe")
    _close(memory)

    assert decision.verdict == "ALLOW"
    assert decision.evidence_count == 1


def test_deleted_memory_layer_returns_memory_required() -> None:
    decision = _decision(
        MemoryFirewall(None), chain="avax", deployer="0xabc", session_id="deleted"
    )

    assert decision.verdict == "MEMORY_REQUIRED"
    assert "MEMORY_UNAVAILABLE" in decision.reason_codes


def test_unavailable_memory_returns_memory_required() -> None:
    class UnavailableMemory:
        def set_reference(self, *_args: object, **_kwargs: object) -> None:
            raise OSError("memory database unavailable")

    decision = _decision(
        MemoryFirewall(UnavailableMemory()),  # type: ignore[arg-type]
        chain="solana",
        deployer="CaseSensitive",
        session_id="offline",
    )

    assert decision.verdict == "MEMORY_REQUIRED"
    assert "OSError" in decision.reason_codes


def test_deployer_entities_are_isolated(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    firewall = MemoryFirewall(memory)
    firewall.record_observation(
        chain="avax", deployer="0xBad", observation=_observation("critical", "bad-only")
    )
    risky = _decision(firewall, chain="avax", deployer="0xbad", session_id="risky")
    clean = _decision(firewall, chain="avax", deployer="0xGood", session_id="clean")
    _close(memory)

    assert risky.verdict == "BLOCK"
    assert clean.verdict == "ALLOW"
    assert clean.evidence_count == 0


def test_chain_specific_address_normalization() -> None:
    assert MemoryFirewall.deployer_key("Avalanche", "0xAbC") == "avax:0xabc"
    assert MemoryFirewall.deployer_key("solana", "AbC123") == "solana:AbC123"


def test_decision_uses_all_required_memory_tiers(tmp_path: Path) -> None:
    memory = MemoryClient.local(str(tmp_path / "memory.db"))
    firewall = MemoryFirewall(memory)
    firewall.record_observation(
        chain="avax", deployer="0xTiered", observation=_observation("warning", "tiered")
    )
    decision = _decision(
        firewall, chain="avax", deployer="0xTiered", session_id="tier-check"
    )

    warm = memory.get_entity("deployer", "avax:0xtiered")
    hot = memory.get_state("analysis:tier-check")
    reference = memory.get_reference("risk-policy-current")
    cold = memory.read_events(limit=10)
    _close(memory)

    assert decision.verdict == "ALLOW"
    assert warm["body"]["observations"][0]["evidence_id"]
    assert hot is not None and hot["body"]["status"] == "complete"
    assert reference is not None
    assert len(cold) >= 2
