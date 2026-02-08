"""Tests for OpenCode scanner."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from gmemory.scanner.opencode import OpenCodeScanner
from gmemory.storage.database import MemoryDatabase
import gmemory.config as cfg
from gmemory.scanner.state import (
    ScanState,
    ScanStateManager,
    FileState,
    compute_file_hash,
)
from gmemory.models import Session


class TestOpenCodeScanner:
    """Tests for OpenCodeScanner class."""

    @pytest.fixture
    def mock_opencode_storage(self, tmp_path):
        """Create mock OpenCode storage structure."""
        storage = tmp_path / "storage"

        # Create session directory structure
        session_dir = storage / "session" / "project1"
        session_dir.mkdir(parents=True)

        # Create session file
        session_file = session_dir / "ses_test001.json"
        session_file.write_text(
            json.dumps(
                {
                    "id": "test001",
                    "directory": "/path/to/project",
                    "title": "Test Project",
                    "time": {"created": "2024-01-01T00:00:00Z"},
                }
            )
        )

        # Create another session
        session_file2 = session_dir / "ses_test002.json"
        session_file2.write_text(
            json.dumps(
                {
                    "id": "test002",
                    "directory": "/path/to/project2",
                    "title": "Test Project 2",
                    "time": {"created": "2024-01-02T00:00:00Z"},
                }
            )
        )

        return tmp_path

    @pytest.fixture
    def mock_storage_with_messages(self, tmp_path):
        """Create mock storage with session, messages, and parts."""
        storage = tmp_path / "storage"

        # Session
        session_dir = storage / "session" / "project1"
        session_dir.mkdir(parents=True)
        session_file = session_dir / "ses_abc123.json"
        session_file.write_text(
            json.dumps(
                {
                    "id": "abc123",
                    "directory": "/my/project",
                    "title": "My Project",
                    "time": {"created": "2024-01-01T10:00:00Z"},
                }
            )
        )

        # Messages
        msg_dir = storage / "message" / "ses_abc123"
        msg_dir.mkdir(parents=True)

        msg1 = msg_dir / "msg_001.json"
        msg1.write_text(json.dumps({"id": "001", "role": "user"}))

        msg2 = msg_dir / "msg_002.json"
        msg2.write_text(json.dumps({"id": "002", "role": "assistant"}))

        # Parts
        part_dir1 = storage / "part" / "msg_001"
        part_dir1.mkdir(parents=True)
        part1 = part_dir1 / "prt_001.json"
        part1.write_text(
            json.dumps({"type": "text", "text": "Hello, can you help me?"})
        )

        part_dir2 = storage / "part" / "msg_002"
        part_dir2.mkdir(parents=True)
        part2 = part_dir2 / "prt_001.json"
        part2.write_text(
            json.dumps({"type": "text", "text": "Of course! How can I assist you?"})
        )

        return tmp_path

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        original_path = cfg.config._config["storage"]["db_path"]
        db_path = tmp_path / "scanner-test.db"
        cfg.config._config["storage"]["db_path"] = str(db_path)
        try:
            yield db_path
        finally:
            cfg.config._config["storage"]["db_path"] = original_path

    @staticmethod
    def _write_session_file(
        base_dir: Path, session_id: str, created: int, title: str
    ) -> Path:
        session_dir = base_dir / "storage" / "session" / "project1"
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / f"ses_{session_id}.json"
        session_file.write_text(
            json.dumps(
                {
                    "id": session_id,
                    "directory": "/path/to/project",
                    "title": title,
                    "time": {"created": created},
                }
            ),
            encoding="utf-8",
        )
        return session_file

    def test_count_sessions(self, mock_opencode_storage):
        """Should count session files correctly."""
        scanner = OpenCodeScanner(base_dir=mock_opencode_storage, incremental=False)
        assert scanner.count_sessions() == 2

    def test_count_sessions_empty(self, tmp_path):
        """Should return 0 for empty storage."""
        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)
        assert scanner.count_sessions() == 0

    def test_count_sessions_no_session_dir(self, tmp_path):
        """Should return 0 when session directory doesn't exist."""
        storage = tmp_path / "storage"
        storage.mkdir()
        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)
        assert scanner.count_sessions() == 0

    def test_get_scan_stats(self, mock_opencode_storage):
        """Should return correct scan statistics."""
        scanner = OpenCodeScanner(base_dir=mock_opencode_storage, incremental=False)
        stats = scanner.get_scan_stats()

        assert stats["total_session_files"] == 2
        assert stats["tracked_files"] == 0  # No incremental tracking

    @patch("gmemory.scanner.opencode.MemoryDatabase")
    def test_get_unprocessed_sessions_empty_dir(self, mock_db_class, tmp_path):
        """Should return empty list when no sessions exist."""
        mock_db = MagicMock()
        mock_db.start_scan_run.return_value = "run_001"
        mock_db_class.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_class.return_value.start_scan_run = mock_db.start_scan_run
        mock_db_class.return_value.finalize_scan_run = mock_db.finalize_scan_run

        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)
        sessions = scanner.get_unprocessed_sessions(limit=10)

        assert sessions == []

    def test_get_unprocessed_sessions_skip_when_version_unchanged(
        self, tmp_path, temp_db_path
    ):
        session_id = "same-version"
        self._write_session_file(
            base_dir=tmp_path,
            session_id=session_id,
            created=100,
            title="Original",
        )

        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)
        with open(
            tmp_path / "storage" / "session" / "project1" / f"ses_{session_id}.json",
            "r",
            encoding="utf-8",
        ) as f:
            session_data = json.load(f)
        source_updated_at, session_hash = scanner._compute_session_version(session_data)

        db = MemoryDatabase()
        try:
            db.mark_session_processed(
                agent=scanner.agent,
                session_id=session_id,
                source_updated_at=source_updated_at,
                session_hash=session_hash,
                processor="default",
            )
        finally:
            db.close()

        sessions = scanner.get_unprocessed_sessions(limit=10)
        assert sessions == []

    def test_get_unprocessed_sessions_reprocess_when_hash_changes(
        self, tmp_path, temp_db_path
    ):
        session_id = "updated-hash"
        session_file = self._write_session_file(
            base_dir=tmp_path,
            session_id=session_id,
            created=100,
            title="Original",
        )

        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)
        with open(session_file, "r", encoding="utf-8") as f:
            old_data = json.load(f)
        source_updated_at, old_hash = scanner._compute_session_version(old_data)

        db = MemoryDatabase()
        try:
            db.mark_session_processed(
                agent=scanner.agent,
                session_id=session_id,
                source_updated_at=source_updated_at,
                session_hash=old_hash,
                processor="default",
            )
        finally:
            db.close()

        self._write_session_file(
            base_dir=tmp_path,
            session_id=session_id,
            created=100,
            title="Updated",
        )

        sessions = scanner.get_unprocessed_sessions(limit=10)
        assert len(sessions) == 1
        assert sessions[0].session_id == session_id

    def test_get_unprocessed_sessions_reprocess_when_latest_processed_is_stale(
        self, tmp_path, temp_db_path
    ):
        session_id = "stale-processed"
        self._write_session_file(
            base_dir=tmp_path,
            session_id=session_id,
            created=200,
            title="Current",
        )

        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)
        with open(
            tmp_path / "storage" / "session" / "project1" / f"ses_{session_id}.json",
            "r",
            encoding="utf-8",
        ) as f:
            session_data = json.load(f)
        _, session_hash = scanner._compute_session_version(session_data)

        db = MemoryDatabase()
        try:
            db.mark_session_processed(
                agent=scanner.agent,
                session_id=session_id,
                source_updated_at=100,
                session_hash=session_hash,
                processor="default",
            )
        finally:
            db.close()

        sessions = scanner.get_unprocessed_sessions(limit=10)
        assert len(sessions) == 1
        assert sessions[0].session_id == session_id

    def test_load_full_session_with_messages(self, mock_storage_with_messages):
        """Should load session with messages and parts."""
        scanner = OpenCodeScanner(
            base_dir=mock_storage_with_messages, incremental=False
        )

        # Load session metadata
        session_file = (
            mock_storage_with_messages
            / "storage"
            / "session"
            / "project1"
            / "ses_abc123.json"
        )
        with open(session_file) as f:
            metadata = json.load(f)

        session = scanner._load_full_session("abc123", metadata)

        assert session is not None
        assert session.session_id == "abc123"
        assert session.project_path == "/my/project"
        assert session.project_name == "My Project"
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert "Hello" in session.messages[0].content
        assert session.messages[1].role == "assistant"
        assert "assist" in session.messages[1].content

    def test_load_session_without_messages(self, tmp_path):
        """Should load session even without message directory."""
        storage = tmp_path / "storage"
        session_dir = storage / "session" / "project1"
        session_dir.mkdir(parents=True)

        session_file = session_dir / "ses_nomsg.json"
        session_file.write_text(
            json.dumps(
                {
                    "id": "nomsg",
                    "directory": "/project",
                    "title": "No Messages",
                    "time": {"created": "2024-01-01T00:00:00Z"},
                }
            )
        )

        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)
        session = scanner._load_full_session(
            "nomsg",
            {
                "id": "nomsg",
                "directory": "/project",
                "title": "No Messages",
                "time": {},
            },
        )

        assert session is not None
        assert session.session_id == "nomsg"
        assert len(session.messages) == 0

    def test_clean_text_strips_private_tags(self, tmp_path):
        """Should strip private tags from content."""
        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)

        text_with_private = "Hello <private>secret</private> world"
        cleaned = scanner._clean_text(text_with_private)

        assert "secret" not in cleaned
        assert "Hello" in cleaned
        assert "world" in cleaned

    def test_clean_text_preserves_unicode(self, tmp_path):
        """Should preserve Unicode characters including Chinese."""
        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)

        text = "Hello 你好 世界 🌍"
        cleaned = scanner._clean_text(text)

        assert "你好" in cleaned
        assert "世界" in cleaned

    def test_clean_text_removes_control_chars(self, tmp_path):
        """Should remove control characters but keep newlines and tabs."""
        scanner = OpenCodeScanner(base_dir=tmp_path, incremental=False)

        text = "Hello\nWorld\tTest\x00\x01"
        cleaned = scanner._clean_text(text)

        assert "\n" in cleaned
        assert "\t" in cleaned
        assert "\x00" not in cleaned
        assert "\x01" not in cleaned


class TestScanState:
    """Tests for ScanState class."""

    def test_is_file_changed_new_file(self, tmp_path):
        """Should detect new files as changed."""
        state = ScanState()
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        assert state.is_file_changed(test_file) is True

    def test_is_file_changed_unchanged(self, tmp_path):
        """Should detect unchanged files."""
        state = ScanState()
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        # Update state
        state.update_file_state(test_file, "session1")

        # File should not be changed
        assert state.is_file_changed(test_file) is False

    def test_is_file_changed_size_changed(self, tmp_path):
        """Should detect size changes."""
        state = ScanState()
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        # Update state
        state.update_file_state(test_file, "session1")

        # Modify file
        test_file.write_text('{"key": "value"}')

        assert state.is_file_changed(test_file) is True

    def test_is_file_changed_content_changed(self, tmp_path):
        """Should detect content changes even with same size."""
        state = ScanState()
        test_file = tmp_path / "test.json"
        test_file.write_text('{"a": 1}')

        # Update state
        state.update_file_state(test_file, "session1")

        # Modify file with same size
        test_file.write_text('{"b": 2}')

        # Force mtime update
        import os
        import time

        os.utime(test_file, (time.time() + 1, time.time() + 1))

        assert state.is_file_changed(test_file) is True

    def test_update_file_state(self, tmp_path):
        """Should correctly update file state."""
        state = ScanState()
        test_file = tmp_path / "test.json"
        test_file.write_text('{"id": "test"}')

        state.update_file_state(test_file, "test_session")

        stored = state.get_file_state(test_file)
        assert stored is not None
        assert stored.last_session_id == "test_session"
        assert stored.size == test_file.stat().st_size

    def test_remove_file_state(self, tmp_path):
        """Should remove file state."""
        state = ScanState()
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        state.update_file_state(test_file, "session1")
        assert state.get_file_state(test_file) is not None

        state.remove_file_state(test_file)
        assert state.get_file_state(test_file) is None


class TestScanStateManager:
    """Tests for ScanStateManager class."""

    def test_load_creates_new_state(self, tmp_path):
        """Should create new state when file doesn't exist."""
        state_file = tmp_path / "state.json"
        manager = ScanStateManager(state_path=state_file)

        state = manager.load()

        assert state is not None
        assert len(state.files) == 0

    def test_save_and_load(self, tmp_path):
        """Should persist state to disk."""
        state_file = tmp_path / "state.json"
        manager = ScanStateManager(state_path=state_file)

        # Create and modify state
        state = manager.load()
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")
        state.update_file_state(test_file, "session1")

        # Save
        manager.save()

        # Load in new manager
        manager2 = ScanStateManager(state_path=state_file)
        state2 = manager2.load()

        assert len(state2.files) == 1
        stored = state2.get_file_state(test_file)
        assert stored is not None
        assert stored.last_session_id == "session1"

    def test_cleanup_missing_files(self, tmp_path):
        """Should remove entries for deleted files."""
        state_file = tmp_path / "state.json"
        manager = ScanStateManager(state_path=state_file)

        # Create file and track it
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        state = manager.load()
        state.update_file_state(test_file, "session1")
        manager.save()

        # Delete the file
        test_file.unlink()

        # Cleanup
        removed = manager.cleanup_missing_files()

        assert removed == 1
        assert len(manager.load().files) == 0


class TestComputeFileHash:
    """Tests for compute_file_hash function."""

    def test_hash_small_file(self, tmp_path):
        """Should hash entire content of small files."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Hello World")

        hash1 = compute_file_hash(test_file)
        hash2 = compute_file_hash(test_file)

        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hex digest

    def test_hash_different_content(self, tmp_path):
        """Should produce different hashes for different content."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content A")
        file2.write_text("Content B")

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)

        assert hash1 != hash2

    def test_hash_nonexistent_file(self, tmp_path):
        """Should return empty string for nonexistent files."""
        nonexistent = tmp_path / "nonexistent.txt"

        result = compute_file_hash(nonexistent)

        assert result == ""
