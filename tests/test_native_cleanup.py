"""Tests for native local ghost cleanup."""

from pathlib import Path

import gmemory.config as cfg
import gmemory.commands.native_cleanup as native_cleanup_module
from gmemory.commands.native_cleanup import cleanup_native_ghost_sessions
from gmemory.models import ProcessedSession
from gmemory.storage.database import MemoryDatabase


class _DummyScanner:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir


def test_native_cleanup_dry_run_and_apply(tmp_path, monkeypatch):
    db_path = tmp_path / "native-cleanup.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    db = MemoryDatabase()
    try:
        db.add_processed_session(
            ProcessedSession(agent="opencode", session_id="native-op-keep")
        )
        db.add_processed_session(
            ProcessedSession(agent="opencode", session_id="native-op-ghost")
        )
        db.add_processed_session(
            ProcessedSession(agent="github-copilot", session_id="native-cp-keep")
        )
        db.add_processed_session(
            ProcessedSession(agent="github-copilot", session_id="native-cp-ghost")
        )

        monkeypatch.setattr(
            native_cleanup_module.ScannerRegistry,
            "list_scanners",
            classmethod(lambda cls: ["opencode", "github-copilot"]),
        )
        monkeypatch.setattr(
            native_cleanup_module.ScannerRegistry,
            "create",
            classmethod(
                lambda cls, name, incremental=False, agent=None: _DummyScanner(tmp_path)
            ),
        )

        def fake_collect(scanner_name, scanner):
            if scanner_name == "opencode":
                return {"native-op-keep"}, 10, 0, True
            if scanner_name == "github-copilot":
                return {"native-cp-keep"}, 8, 0, True
            return set(), 0, 0, False

        monkeypatch.setattr(
            native_cleanup_module,
            "_collect_native_session_ids",
            fake_collect,
        )

        preview = cleanup_native_ghost_sessions(
            scanner_type="all",
            dry_run=True,
            limit=50,
        )
        assert preview["dry_run"] is True
        assert preview["candidate_count"] == 2
        assert preview["by_scanner"]["opencode"] == 1
        assert preview["by_scanner"]["github-copilot"] == 1
        assert "confirm_token" in preview

        applied = cleanup_native_ghost_sessions(
            scanner_type="all",
            dry_run=False,
            limit=50,
            confirm_token=preview["confirm_token"],
        )
        assert applied["dry_run"] is False
        assert applied["deleted"] == 2
        assert db.get_processed_session_count("opencode") == 1
        assert db.get_processed_session_count("github-copilot") == 1
    finally:
        db.close()
        cfg.config._config["storage"]["db_path"] = original_db_path


def test_native_cleanup_respects_limit(tmp_path, monkeypatch):
    db_path = tmp_path / "native-cleanup-limit.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    db = MemoryDatabase()
    try:
        db.add_processed_session(
            ProcessedSession(agent="opencode", session_id="limit-ghost-001")
        )
        db.add_processed_session(
            ProcessedSession(agent="opencode", session_id="limit-ghost-002")
        )
        db.add_processed_session(
            ProcessedSession(agent="opencode", session_id="limit-ghost-003")
        )

        monkeypatch.setattr(
            native_cleanup_module.ScannerRegistry,
            "list_scanners",
            classmethod(lambda cls: ["opencode"]),
        )
        monkeypatch.setattr(
            native_cleanup_module.ScannerRegistry,
            "create",
            classmethod(
                lambda cls, name, incremental=False, agent=None: _DummyScanner(tmp_path)
            ),
        )
        monkeypatch.setattr(
            native_cleanup_module,
            "_collect_native_session_ids",
            lambda scanner_name, scanner: (set(), 3, 0, True),
        )

        first_apply = cleanup_native_ghost_sessions(
            scanner_type="opencode",
            dry_run=False,
            limit=2,
            confirm_token="confirm-native-cleanup:opencode:2",
        )
        assert first_apply["candidate_count"] == 2
        assert first_apply["deleted"] == 2
        assert db.get_processed_session_count("opencode") == 1

        second_apply = cleanup_native_ghost_sessions(
            scanner_type="opencode",
            dry_run=False,
            limit=2,
            confirm_token="confirm-native-cleanup:opencode:2",
        )
        assert second_apply["candidate_count"] == 1
        assert second_apply["deleted"] == 1
        assert db.get_processed_session_count("opencode") == 0
    finally:
        db.close()
        cfg.config._config["storage"]["db_path"] = original_db_path


def test_native_cleanup_apply_requires_confirm_token(tmp_path, monkeypatch):
    db_path = tmp_path / "native-cleanup-token.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    db = MemoryDatabase()
    try:
        db.add_processed_session(
            ProcessedSession(agent="opencode", session_id="ghost-needs-token")
        )
        monkeypatch.setattr(
            native_cleanup_module.ScannerRegistry,
            "list_scanners",
            classmethod(lambda cls: ["opencode"]),
        )
        monkeypatch.setattr(
            native_cleanup_module.ScannerRegistry,
            "create",
            classmethod(
                lambda cls, name, incremental=False, agent=None: _DummyScanner(tmp_path)
            ),
        )
        monkeypatch.setattr(
            native_cleanup_module,
            "_collect_native_session_ids",
            lambda scanner_name, scanner: (set(), 1, 0, True),
        )

        blocked = cleanup_native_ghost_sessions(
            scanner_type="opencode",
            dry_run=False,
            limit=100,
        )
        assert blocked["error_code"] == "VALIDATION_ERROR"
    finally:
        db.close()
        cfg.config._config["storage"]["db_path"] = original_db_path
