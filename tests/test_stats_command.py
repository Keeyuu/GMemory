"""Tests for stats command session counting semantics."""

from pathlib import Path

import gmemory.config as cfg
import gmemory.commands.stats as stats_module
from gmemory.models import ProcessedSession
from gmemory.storage.database import MemoryDatabase


def test_get_stats_counts_only_processed_sessions_present_in_native_source(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "stats-counting.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    original_default_scanner = cfg.config._config["scanner"]["default_scanner"]
    cfg.config._config["storage"]["db_path"] = str(db_path)
    cfg.config._config["scanner"]["default_scanner"] = "all"

    db = MemoryDatabase()
    try:
        db.add_processed_session(ProcessedSession(agent="opencode", session_id="s-001"))
        db.add_processed_session(ProcessedSession(agent="sisyphus", session_id="s-002"))
        db.add_processed_session(
            ProcessedSession(agent="opencode", session_id="ghost-999")
        )
    finally:
        db.close()

    monkeypatch.setattr(
        stats_module.ScannerRegistry,
        "list_scanners",
        classmethod(lambda cls: ["opencode"]),
    )
    monkeypatch.setattr(
        stats_module,
        "get_native_session_snapshot",
        lambda scanner_name: {
            "scanner": scanner_name,
            "supported": True,
            "session_ids": {"s-001", "s-002", "s-003"},
            "native_files": 3,
            "parse_errors": 0,
        },
    )

    try:
        result = stats_module.get_stats()
        assert result["unprocessed_sessions"] == 1
        assert "reprocess_rate" in result
        assert "hash_mismatch_rate" in result
        assert result["ghost_count"] == 1
        assert "cleanup_deleted_rows" in result
    finally:
        cfg.config._config["storage"]["db_path"] = original_db_path
        cfg.config._config["scanner"]["default_scanner"] = original_default_scanner
