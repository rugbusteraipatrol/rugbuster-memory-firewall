from pathlib import Path

from sibyl_memory_client import MemoryClient


def _close(memory: MemoryClient) -> None:
    # MemoryClient 0.7.0 does not expose a public close method.
    memory._storage.close()  # type: ignore[attr-defined]


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

