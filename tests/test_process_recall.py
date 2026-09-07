import json
import subprocess
import sys
from pathlib import Path

from sibyl_memory_client import MemoryClient
from rugbuster_memory_firewall import MemoryFirewall, VerifiedObservation

ROOT = Path(__file__).resolve().parents[1]


def test_reader_recalls_after_parent_closes_storage(tmp_path: Path) -> None:
    case = json.loads((ROOT / "evidence/avax-repeat-deployer-case.json").read_text())
    db = tmp_path / "memory.db"
    memory = MemoryClient.local(str(db))
    try:
        firewall = MemoryFirewall(memory)
        for index in range(2):
            firewall.record_observation(
                chain=case["chain"], deployer=case["deployer"],
                observation=VerifiedObservation.now(
                    kind="critical", source="synthetic-process-test",
                    evidence_uri=f"fixture://process-{index}", details="Synthetic persistence test only.",
                ),
            )
    finally:
        memory._storage.close()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/process_recall_proof.py"), "--stage", "read", "--db", str(db)],
        capture_output=True, text=True, timeout=30, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "separate_process_recall=PASSED" in result.stdout
    assert '"evidence_count": 2' in result.stdout


def test_reader_does_not_recreate_missing_database(tmp_path: Path) -> None:
    db = tmp_path / "missing.db"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/process_recall_proof.py"), "--stage", "read", "--db", str(db)],
        capture_output=True, text=True, timeout=30, cwd=ROOT,
    )
    assert result.returncode != 0
    assert not db.exists()
    assert "Persisted database missing" in result.stderr
