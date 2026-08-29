"""Verify the pinned Sibyl SDK without touching the user's real memory DB."""

from __future__ import annotations

import importlib.metadata
import tempfile
from pathlib import Path

from sibyl_memory_client import FREE_TIER_CAP_BYTES, MemoryClient


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="rugbuster-sibyl-check-") as temp_dir:
        db_path = Path(temp_dir) / "memory.db"
        memory = MemoryClient.local(str(db_path))
        memory.set_entity(
            "environment_check",
            "rugbuster",
            {"status": "ready", "purpose": "pre-build SDK verification"},
        )
        memory._storage.close()  # type: ignore[attr-defined]

        # Reopen the database to prove that recall survives a fresh client.
        fresh_memory = MemoryClient.local(str(db_path))
        recalled = fresh_memory.get_entity("environment_check", "rugbuster")
        db_bytes = db_path.stat().st_size if db_path.exists() else 0

        print(f"sibyl-memory-client={importlib.metadata.version('sibyl-memory-client')}")
        print(f"sibyl-memory-cli={importlib.metadata.version('sibyl-memory-cli')}")
        print(f"database_created={db_path.exists()}")
        print(f"database_bytes={db_bytes}")
        print(f"free_cap_bytes={FREE_TIER_CAP_BYTES}")
        print(f"cap_used_percent={db_bytes / FREE_TIER_CAP_BYTES * 100:.4f}")
        print(f"fresh_client_recall_ok={bool(recalled and recalled.get('body', {}).get('status') == 'ready')}")

        # MemoryClient 0.7.0 has no public close method. Close its storage handle
        # so Windows can remove the temporary verification database cleanly.
        fresh_memory._storage.close()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
