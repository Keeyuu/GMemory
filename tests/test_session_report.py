"""Tests for session report functionality."""

import pytest
import tempfile
from pathlib import Path

from gmemory.models import Memory
from gmemory.storage.database import MemoryDatabase
from gmemory.commands.session_report import get_session_report, get_session_detail


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        import gmemory.config as cfg

        original_path = cfg.config._config["storage"]["db_path"]
        cfg.config._config["storage"]["db_path"] = str(db_path)

        db = MemoryDatabase()
        yield db
        db.close()

        cfg.config._config["storage"]["db_path"] = original_path


class TestSessionReport:
    """Tests for session aggregation report."""

    def test_empty_report(self, temp_db):
        """Should return empty report when no memories exist."""
        result = get_session_report(limit=10)

        assert result["total_sessions"] == 0
        assert result["total_memories"] == 0
        assert result["sessions"] == []

    def test_report_with_memories(self, temp_db):
        """Should aggregate memories by session."""
        # Add memories with different sessions
        memory1 = Memory(
            id="mem-001",
            content="First memory",
            tags=["python", "api"],
            importance="high",
            source_session_id="session-001",
            project_path="/project/a",
        )
        memory2 = Memory(
            id="mem-002",
            content="Second memory",
            tags=["python", "database"],
            importance="medium",
            source_session_id="session-001",
            project_path="/project/a",
        )
        memory3 = Memory(
            id="mem-003",
            content="Third memory",
            tags=["javascript"],
            importance="low",
            source_session_id="session-002",
            project_path="/project/b",
        )

        temp_db.add_memory(memory1)
        temp_db.add_memory(memory2)
        temp_db.add_memory(memory3)

        result = get_session_report(limit=10)

        assert result["total_sessions"] == 2
        assert result["total_memories"] == 3

        # Find session-001 in results
        session_001 = next(
            (s for s in result["sessions"] if s["session_id"] == "session-001"), None
        )
        assert session_001 is not None
        assert session_001["memory_count"] == 2
        assert session_001["importance_breakdown"]["high"] == 1
        assert session_001["importance_breakdown"]["medium"] == 1

    def test_session_detail(self, temp_db):
        """Should return detailed session information."""
        memory = Memory(
            id="mem-detail-001",
            content="Detailed memory content for testing",
            tags=["test", "detail"],
            importance="high",
            source_session_id="session-detail",
            project_path="/project/test",
        )
        temp_db.add_memory(memory)

        result = get_session_detail("session-detail")

        assert result["found"] is True
        assert result["session_id"] == "session-detail"
        assert result["memory_count"] == 1
        assert len(result["memories"]) == 1
        assert "preview" in result["memories"][0]

    def test_session_detail_with_full_content(self, temp_db):
        """Should include full content when requested."""
        memory = Memory(
            id="mem-full-001",
            content="Full content that should be included",
            tags=["test"],
            source_session_id="session-full",
        )
        temp_db.add_memory(memory)

        result = get_session_detail("session-full", include_content=True)

        assert result["found"] is True
        assert "content" in result["memories"][0]
        assert (
            result["memories"][0]["content"] == "Full content that should be included"
        )

    def test_session_detail_not_found(self, temp_db):
        """Should return not found for nonexistent session."""
        result = get_session_detail("nonexistent-session")

        assert result["found"] is False
        assert "error" in result
