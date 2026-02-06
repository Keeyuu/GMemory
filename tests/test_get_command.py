"""Tests for get command access tracking behavior."""

import tempfile
from pathlib import Path

import pytest

from gmemory.commands.get import get_memories
from gmemory.models import Memory
from gmemory.storage.database import MemoryDatabase


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary DB path and override global config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test-get.db"
        import gmemory.config as cfg

        original_path = cfg.config._config["storage"]["db_path"]
        cfg.config._config["storage"]["db_path"] = str(db_path)
        try:
            yield db_path
        finally:
            cfg.config._config["storage"]["db_path"] = original_path


def test_get_memories_tracks_access_by_default(temp_db_path: Path) -> None:
    db = MemoryDatabase()
    try:
        db.add_memory(Memory(id="get-track-001", content="Track me"))
    finally:
        db.close()

    result = get_memories(ids=["get-track-001"], include_metadata=True)
    assert result["found"] == 1
    assert result["results"][0]["access_count"] == 1

    verify_db = MemoryDatabase()
    try:
        memory = verify_db.get_memory("get-track-001")
        assert memory is not None
        assert memory.access_count == 1
        assert memory.last_accessed_at is not None
    finally:
        verify_db.close()


def test_get_memories_can_skip_access_tracking(temp_db_path: Path) -> None:
    db = MemoryDatabase()
    try:
        db.add_memory(Memory(id="get-track-002", content="Do not track"))
    finally:
        db.close()

    result = get_memories(
        ids=["get-track-002"], include_metadata=True, track_access=False
    )
    assert result["found"] == 1
    assert result["results"][0]["access_count"] == 0

    verify_db = MemoryDatabase()
    try:
        memory = verify_db.get_memory("get-track-002")
        assert memory is not None
        assert memory.access_count == 0
        assert memory.last_accessed_at is None
    finally:
        verify_db.close()


def test_get_memories_uses_stored_preview_when_present(temp_db_path: Path) -> None:
    db = MemoryDatabase()
    try:
        db.add_memory(
            Memory(
                id="get-preview-001",
                content="This is full memory content that should not be used as preview.",
                preview="Agent-authored preview",
            )
        )
    finally:
        db.close()

    result = get_memories(
        ids=["get-preview-001"], include_metadata=True, track_access=False
    )
    assert result["found"] == 1
    assert result["results"][0]["preview"] == "Agent-authored preview"
