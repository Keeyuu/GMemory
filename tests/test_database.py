"""Tests for database operations."""

import pytest
import tempfile
import os
from pathlib import Path

from gmemory.models import Memory
from gmemory.storage.database import MemoryDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        # Temporarily override config
        import gmemory.config as cfg

        original_path = cfg.config._config["storage"]["db_path"]
        cfg.config._config["storage"]["db_path"] = str(db_path)

        db = MemoryDatabase()
        yield db
        db.close()

        # Restore original config
        cfg.config._config["storage"]["db_path"] = original_path


class TestMemoryDatabase:
    """Tests for MemoryDatabase class."""

    def test_add_and_get_memory(self, temp_db):
        """Should add and retrieve a memory."""
        memory = Memory(
            id="test-001",
            content="Test memory content",
            tags=["test", "unit"],
            importance="high",
        )

        temp_db.add_memory(memory)
        retrieved = temp_db.get_memory("test-001")

        assert retrieved is not None
        assert retrieved.id == "test-001"
        assert retrieved.content == "Test memory content"
        assert "test" in retrieved.tags

    def test_update_memory(self, temp_db):
        """Should update an existing memory."""
        memory = Memory(
            id="test-002",
            content="Original content",
            tags=["original"],
        )
        temp_db.add_memory(memory)

        memory.content = "Updated content"
        memory.tags = ["updated"]
        temp_db.update_memory(memory)

        retrieved = temp_db.get_memory("test-002")
        assert retrieved.content == "Updated content"
        assert "updated" in retrieved.tags

    def test_delete_memory(self, temp_db):
        """Should delete a memory."""
        memory = Memory(
            id="test-003",
            content="To be deleted",
        )
        temp_db.add_memory(memory)

        temp_db.delete_memory("test-003")
        retrieved = temp_db.get_memory("test-003")

        assert retrieved is None

    def test_get_nonexistent_memory(self, temp_db):
        """Should return None for nonexistent memory."""
        retrieved = temp_db.get_memory("nonexistent-id")
        assert retrieved is None

    def test_fts_search(self, temp_db):
        """Should find memories using FTS."""
        memory1 = Memory(
            id="fts-001",
            content="Python programming language",
            tags=["python", "programming"],
        )
        memory2 = Memory(
            id="fts-002",
            content="JavaScript web development",
            tags=["javascript", "web"],
        )
        temp_db.add_memory(memory1)
        temp_db.add_memory(memory2)

        results = temp_db.search_fts("Python", limit=10)

        assert len(results) >= 1
        memory_ids = [r[0] for r in results]
        assert "fts-001" in memory_ids

    def test_stats(self, temp_db):
        """Should return correct statistics."""
        memory = Memory(id="stats-001", content="Test")
        temp_db.add_memory(memory)

        stats = temp_db.get_stats()

        assert "memories" in stats
        assert stats["memories"] >= 1
        assert "scan_runs" in stats
        assert "scan_errors" in stats

    def test_scan_runs_and_errors(self, temp_db):
        """Should track scan runs and scan errors."""
        stats_before = temp_db.get_stats()
        run_id = temp_db.start_scan_run(
            scanner="opencode",
            agent="opencode",
            base_dir="/tmp/opencode",
            incremental=True,
            limit_value=3,
        )

        temp_db.add_scan_error(
            run_id=run_id,
            file_path="/tmp/opencode/storage/session/ses_1.json",
            session_id="ses_1",
            error_code="GMEM-SCN-302",
            error_message="Parse error",
        )

        temp_db.finalize_scan_run(
            run_id=run_id,
            status="completed",
            total_files=1,
            scanned_files=1,
            skipped_unchanged=0,
            unprocessed_sessions=0,
            error_count=1,
            limit_reached=False,
            note=None,
        )

        stats_after = temp_db.get_stats()
        assert stats_after["scan_runs"] == stats_before["scan_runs"] + 1

        runs = temp_db.get_scan_runs(limit=5)
        assert len(runs) >= 1
        assert runs[0]["id"] == run_id

        errors = temp_db.get_scan_errors(limit=5)
        assert len(errors) >= 1
        assert errors[0]["run_id"] == run_id

        resolve_result = temp_db.resolve_scan_errors([errors[0]["id"]], note="reviewed")
        assert errors[0]["id"] in resolve_result["resolved"]

        unresolved = temp_db.get_scan_errors(limit=5, unresolved_only=True)
        assert len(unresolved) == 0

    def test_diagnostics_include_scan(self, temp_db):
        """Diagnostics should include scan run and error counts."""
        run_id = temp_db.start_scan_run(
            scanner="opencode",
            agent="opencode",
            base_dir="/tmp/opencode",
            incremental=False,
            limit_value=1,
        )
        temp_db.add_scan_error(
            run_id=run_id,
            file_path=None,
            session_id=None,
            error_code="GMEM-SCN-302",
            error_message="Parse error",
        )
        temp_db.finalize_scan_run(
            run_id=run_id,
            status="completed",
            total_files=0,
            scanned_files=0,
            skipped_unchanged=0,
            unprocessed_sessions=0,
            error_count=1,
            limit_reached=False,
            note=None,
        )

        diag = temp_db.get_diagnostics()
        assert "scan_runs" in diag
        assert "scan_errors" in diag

    def test_touch_memory_access(self, temp_db):
        """Should increment access_count and set last_accessed_at."""
        memory = Memory(id="access-001", content="Access test")
        temp_db.add_memory(memory)

        updated = temp_db.touch_memory_access("access-001")
        assert updated is True

        retrieved = temp_db.get_memory("access-001")
        assert retrieved is not None
        assert retrieved.access_count == 1
        assert retrieved.last_accessed_at is not None

    def test_hot_and_cold_memories(self, temp_db):
        """Should return hot/cold memory summaries by access signals."""
        old_ts = 1_700_000_000
        temp_db.add_memory(
            Memory(
                id="hot-001",
                content="Hot memory",
                tags=["hot"],
                created_at=old_ts,
                updated_at=old_ts,
            )
        )
        temp_db.add_memory(
            Memory(
                id="cold-001",
                content="Cold memory",
                tags=["cold"],
                created_at=old_ts,
                updated_at=old_ts,
            )
        )

        temp_db.touch_memory_access("hot-001")
        temp_db.touch_memory_access("hot-001")

        hot = temp_db.get_hot_memories(limit=3)
        cold = temp_db.get_cold_memories(limit=3, min_age_days=1)

        assert len(hot) >= 1
        assert hot[0]["id"] == "hot-001"
        assert hot[0]["access_count"] >= 2
        assert len(cold) >= 1
        assert any(item["id"] == "cold-001" for item in cold)
