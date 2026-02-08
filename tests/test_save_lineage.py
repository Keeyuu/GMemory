import tempfile
from pathlib import Path

import gmemory.config as cfg
from gmemory.commands.list import list_memories
from gmemory.commands.save import save_memory
from gmemory.storage.database import MemoryDatabase


def test_save_memory_supersedes_previous_session_memory():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "save-lineage.db"
        original_path = cfg.config._config["storage"]["db_path"]
        cfg.config._config["storage"]["db_path"] = str(db_path)

        try:
            first = save_memory(
                session_id="session-lineage-001",
                content="first insight",
                tags=["a"],
                require_embedding=False,
            )
            second = save_memory(
                session_id="session-lineage-001",
                content="updated insight",
                tags=["a", "b"],
                require_embedding=False,
            )

            assert first["created"] is True
            assert second["created"] is True
            assert first["memory_id"] != second["memory_id"]

            db = MemoryDatabase()
            try:
                first_memory = db.get_memory(first["memory_id"])
                second_memory = db.get_memory(second["memory_id"])
                assert first_memory is not None
                assert second_memory is not None
                assert first_memory.superseded_by == second_memory.id

                active = db.get_active_memory_by_source_session(
                    agent=cfg.config.default_agent,
                    source_session_id="session-lineage-001",
                )
                assert active is not None
                assert active.id == second_memory.id
            finally:
                db.close()
        finally:
            cfg.config._config["storage"]["db_path"] = original_path


def test_save_memory_same_payload_is_idempotent_for_lineage():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "save-idempotent.db"
        original_path = cfg.config._config["storage"]["db_path"]
        cfg.config._config["storage"]["db_path"] = str(db_path)

        try:
            first = save_memory(
                session_id="session-lineage-002",
                content="same insight",
                tags=["x"],
                importance="medium",
                memory_type="observation",
                require_embedding=False,
            )
            replay = save_memory(
                session_id="session-lineage-002",
                content="same insight",
                tags=["x"],
                importance="medium",
                memory_type="observation",
                require_embedding=False,
            )

            assert first["created"] is True
            assert replay["created"] is False
            assert replay["memory_id"] == first["memory_id"]

            listed = list_memories(limit=50, include_superseded=True)
            db = MemoryDatabase()
            try:
                rows = db.conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE source_session_id = ?",
                    ("session-lineage-002",),
                ).fetchone()
                assert rows is not None
                assert rows[0] == 1
                assert any(
                    item["id"] == first["memory_id"] for item in listed["results"]
                )
            finally:
                db.close()
        finally:
            cfg.config._config["storage"]["db_path"] = original_path


def test_list_memories_excludes_superseded_by_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "save-list-filter.db"
        original_path = cfg.config._config["storage"]["db_path"]
        cfg.config._config["storage"]["db_path"] = str(db_path)

        try:
            first = save_memory(
                session_id="session-lineage-003",
                content="old content",
                tags=["k"],
                require_embedding=False,
            )
            second = save_memory(
                session_id="session-lineage-003",
                content="new content",
                tags=["k"],
                require_embedding=False,
            )

            listed = list_memories(limit=20)
            listed_ids = {item["id"] for item in listed["results"]}

            assert second["memory_id"] in listed_ids
            assert first["memory_id"] not in listed_ids
        finally:
            cfg.config._config["storage"]["db_path"] = original_path
