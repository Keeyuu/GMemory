"""Tests for external provider session import queue behavior."""

import json
import shutil
from pathlib import Path

import gmemory.config as cfg
from gmemory.commands.fetch import fetch_unprocessed_sessions
from gmemory.commands.import_external import import_external_provider_data
from gmemory.commands.mark import mark_session
from gmemory.storage.database import MemoryDatabase
import gmemory.commands.fetch as fetch_module


def _create_opencode_session(
    base_dir: Path, session_id: str = "ext-session-001"
) -> None:
    session_dir = base_dir / "storage" / "session" / "project-1"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / f"ses_{session_id}.json"
    session_file.write_text(
        json.dumps(
            {
                "id": session_id,
                "title": "External Session",
                "directory": "C:/external/project",
                "time": {"created": 1770000000},
            }
        ),
        encoding="utf-8",
    )


def test_external_import_queues_sessions_without_creating_memories(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "import-external.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    try:
        source_dir = tmp_path / "external-opencode"
        _create_opencode_session(source_dir, session_id="ext-session-001")

        result = import_external_provider_data(
            folder_path=str(source_dir),
            scanner_type="opencode",
            limit=100,
        )

        assert result["queued"] == 1
        assert result["updated"] == 0
        assert result["failed"] == 0
        assert result["pending_unprocessed"] == 1

        db = MemoryDatabase()
        try:
            # Import should queue sessions only, not create memories.
            assert db.get_stats()["memories"] == 0
            pending = db.get_unprocessed_imported_sessions(limit=10, agent="opencode")
            assert len(pending) == 1
            assert pending[0].session_id == "ext-session-001"
        finally:
            db.close()

        # Source directory can be removed after import; queued session remains processable.
        shutil.rmtree(source_dir)
        monkeypatch.setattr(
            fetch_module.ScannerRegistry,
            "list_scanners",
            classmethod(lambda cls: []),
        )

        fetched = fetch_unprocessed_sessions(limit=10, agent="all", scanner_type="all")
        assert fetched["has_more"] is False
        assert len(fetched["sessions"]) == 1
        assert fetched["sessions"][0]["session_id"] == "ext-session-001"

        # Mark processed should remove it from pending backlog.
        mark_session(session_id="ext-session-001")
        fetched_after = fetch_unprocessed_sessions(
            limit=10, agent="all", scanner_type="all"
        )
        assert fetched_after["sessions"] == []
    finally:
        cfg.config._config["storage"]["db_path"] = original_db_path


def test_external_import_accepts_copilot_alias(tmp_path):
    db_path = tmp_path / "import-copilot-alias.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    try:
        source_dir = tmp_path / "external-copilot"
        source_dir.mkdir(parents=True, exist_ok=True)

        result = import_external_provider_data(
            folder_path=str(source_dir),
            scanner_type="copilot",
            limit=100,
        )

        assert result["scanner_type"] == "github-copilot"
        assert result["queued"] == 0
        assert result["failed"] == 0
    finally:
        cfg.config._config["storage"]["db_path"] = original_db_path
