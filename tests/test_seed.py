import json
from pathlib import Path

from sibyl_memory_client import MemoryClient

from rugbuster_memory_firewall import MemoryFirewall
from rugbuster_memory_firewall.seed import seed_verified_case


def test_verified_case_seed_is_idempotent_across_restarts(tmp_path: Path) -> None:
    artifact = Path("evidence/avax-repeat-deployer-case.json")
    case = json.loads(artifact.read_text(encoding="utf-8"))
    db_path = tmp_path / "memory.db"

    first = MemoryClient.local(str(db_path))
    assert seed_verified_case(first, artifact) == 2
    first._storage.close()  # type: ignore[attr-defined]

    second = MemoryClient.local(str(db_path))
    assert seed_verified_case(second, artifact) == 2
    target = case["recall_target"]
    decision = MemoryFirewall(second).pre_sign(
        chain=case["chain"],
        token_address=target["token_address"],
        deployer=case["deployer"],
        current_risk="clean",
        action={"type": "swap", "asset": target["token_address"]},
        session_id="production-seed-test",
    )
    second._storage.close()  # type: ignore[attr-defined]

    assert decision.verdict == "BLOCK"
    assert decision.evidence_count == 2
    assert decision.reason_codes == ("BLOCK_REPEAT_DEPLOYER",)
