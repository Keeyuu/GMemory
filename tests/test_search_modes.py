"""Tests for search mode branches."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import time

from gmemory.commands.search import (
    search_memories,
    _filter_and_format,
    _hybrid_search_with_scores,
)
from gmemory.models import Memory
from gmemory.storage.embedder import NoOpEmbedder


class TestSearchModes:
    """Tests for different search modes."""

    @pytest.fixture
    def mock_container(self):
        """Create mock container with database and embedder."""
        mock_db = MagicMock()
        mock_embedder = MagicMock()
        mock_config = MagicMock()

        # Configure mock config
        mock_config.search_default_limit = 10
        mock_config.search_min_score_threshold = 0.2
        mock_config.search_default_mode = "hybrid"
        mock_config.search_recency_weight = 0.0
        mock_config.search_use_tag_index = False
        mock_config.search_tag_weight = 0.3
        mock_config.search_recency_window_days = 90
        mock_config.embedding_dimension = 768

        # Configure mock embedder
        mock_embedder.dimension = 768
        mock_embedder.embed.return_value = [0.1] * 768

        # Configure mock database
        mock_db.search_memories.return_value = []
        mock_db.search_fts.return_value = []
        mock_db.search_tags.return_value = []
        mock_db.has_tag_index.return_value = False
        mock_db.get_memory.return_value = None

        mock_container = MagicMock()
        mock_container.get_database.return_value = mock_db
        mock_container.get_embedder.return_value = mock_embedder
        mock_container.get_config.return_value = mock_config

        return mock_container, mock_db, mock_embedder, mock_config

    @patch("gmemory.commands.search.get_container")
    def test_fts_only_mode(self, mock_get_container, mock_container):
        """FTS mode should not require embeddings."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        # Setup FTS results
        mock_db.search_fts.return_value = [("mem1", 1.0), ("mem2", 2.0)]
        mock_db.get_memory.side_effect = [
            Memory(
                id="mem1",
                content="Python tutorial",
                created_at=int(time.time()),
                updated_at=int(time.time()),
            ),
            Memory(
                id="mem2",
                content="Python basics",
                created_at=int(time.time()),
                updated_at=int(time.time()),
            ),
        ]

        result = search_memories("python", mode="fts", limit=5)

        assert result["mode"] == "fts"
        assert "error" not in result
        # Embedder should not be called in FTS mode
        mock_embedder.embed.assert_not_called()

    @patch("gmemory.commands.search.get_container")
    def test_vector_mode(self, mock_get_container, mock_container):
        """Vector mode should use embeddings only."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        mem = Memory(
            id="mem1",
            content="Python tutorial",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        mock_db.search_memories.return_value = [(mem, 0.1)]

        result = search_memories("python", mode="vector", limit=5)

        assert result["mode"] == "vector"
        assert "error" not in result
        mock_embedder.embed.assert_called_once_with("python")

    @patch("gmemory.commands.search.get_container")
    def test_hybrid_mode_default(self, mock_get_container, mock_container):
        """Hybrid mode should combine vector and FTS."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        mem = Memory(
            id="mem1",
            content="Python tutorial",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        mock_db.search_memories.return_value = [(mem, 0.1)]
        mock_db.search_fts.return_value = [("mem1", 1.0)]

        result = search_memories("python", mode="hybrid", limit=5)

        assert result["mode"] == "hybrid"
        assert "error" not in result
        mock_embedder.embed.assert_called()
        mock_db.search_memories.assert_called()
        mock_db.search_fts.assert_called()

    @patch("gmemory.commands.search.get_container")
    def test_fallback_to_fts_on_noop_embedder(self, mock_get_container, mock_container):
        """Should fallback to FTS when embedder is NoOpEmbedder."""
        container, mock_db, _, mock_config = mock_container
        mock_get_container.return_value = container

        # Use NoOpEmbedder
        noop_embedder = NoOpEmbedder()
        container.get_embedder.return_value = noop_embedder

        mock_db.search_fts.return_value = [("mem1", 1.0)]
        mock_db.get_memory.return_value = Memory(
            id="mem1",
            content="Test",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

        result = search_memories("python", mode="hybrid", limit=5)

        assert result["mode"] == "fts"
        assert "warning" in result
        assert "unavailable" in result["warning"].lower()

    @patch("gmemory.commands.search.get_container")
    def test_fallback_to_fts_on_embedding_failure(
        self, mock_get_container, mock_container
    ):
        """Should fallback to FTS when embedding fails."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        # Make embedding fail
        mock_embedder.embed.side_effect = Exception("Embedding failed")

        mock_db.search_fts.return_value = [("mem1", 1.0)]
        mock_db.get_memory.return_value = Memory(
            id="mem1",
            content="Test",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

        result = search_memories("python", mode="hybrid", limit=5)

        assert result["mode"] == "fts"
        assert "warning" in result

    @patch("gmemory.commands.search.get_container")
    def test_profile_override(self, mock_get_container, mock_container):
        """CLI options should override profile settings."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        mem = Memory(
            id="mem1",
            content="Python",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        mock_db.search_memories.return_value = [(mem, 0.1)]
        mock_db.search_fts.return_value = []

        # Use 'recent' profile but override recency_weight to 0.0
        result = search_memories(
            "python", profile="recent", recency_weight=0.0, limit=5
        )

        # Should use profile but with overridden recency
        assert "error" not in result
        assert result.get("profile") == "recent"

    @patch("gmemory.commands.search.get_container")
    def test_unknown_profile_error(self, mock_get_container, mock_container):
        """Should return error for unknown profile."""
        container, _, _, _ = mock_container
        mock_get_container.return_value = container

        result = search_memories("python", profile="nonexistent")

        assert "error" in result
        assert "nonexistent" in result["error"]

    @patch("gmemory.commands.search.get_container")
    def test_compact_mode_output(self, mock_get_container, mock_container):
        """Compact mode should return preview instead of full content."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        long_content = "A" * 200
        mem = Memory(
            id="mem1",
            content=long_content,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        mock_db.search_memories.return_value = [(mem, 0.1)]
        mock_db.search_fts.return_value = []

        result = search_memories("test", mode="vector", limit=5, compact=True)

        assert len(result["results"]) > 0
        first_result = result["results"][0]
        assert "preview" in first_result
        assert "content" not in first_result
        assert len(first_result["preview"]) <= 153  # 150 + "..."

    @patch("gmemory.commands.search.get_container")
    def test_explain_mode_includes_scoring(self, mock_get_container, mock_container):
        """Explain mode should include scoring breakdown."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        mem = Memory(
            id="mem1",
            content="Python",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        mock_db.search_memories.return_value = [(mem, 0.1)]
        mock_db.search_fts.return_value = [("mem1", 1.0)]

        result = search_memories("python", mode="hybrid", limit=5, explain=True)

        assert "scoring_config" in result
        assert "vector_weight" in result["scoring_config"]
        assert "fts_weight" in result["scoring_config"]

    @patch("gmemory.commands.search.get_container")
    def test_tag_filter(self, mock_get_container, mock_container):
        """Should filter results by tags."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        mem1 = Memory(
            id="mem1",
            content="Python",
            tags=["python", "tutorial"],
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        mem2 = Memory(
            id="mem2",
            content="Java",
            tags=["java"],
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

        mock_db.search_memories.return_value = [(mem1, 0.1), (mem2, 0.2)]
        mock_db.search_fts.return_value = []

        result = search_memories("programming", mode="vector", limit=5, tags=["python"])

        # Only mem1 should be in results (has python tag)
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "mem1"

    @patch("gmemory.commands.search.get_container")
    def test_project_path_filter(self, mock_get_container, mock_container):
        """Should filter results by project path."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        mem1 = Memory(
            id="mem1",
            content="Code",
            project_path="/project/a",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        mem2 = Memory(
            id="mem2",
            content="Code",
            project_path="/project/b",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

        mock_db.search_memories.return_value = [(mem1, 0.1), (mem2, 0.2)]
        mock_db.search_fts.return_value = []

        result = search_memories(
            "code", mode="vector", limit=5, project_path="/project/a"
        )

        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "mem1"

    @patch("gmemory.commands.search.get_container")
    def test_min_score_threshold(self, mock_get_container, mock_container):
        """Should filter out results below min_score threshold."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        # High distance = low similarity
        mem1 = Memory(
            id="mem1",
            content="Good match",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        mem2 = Memory(
            id="mem2",
            content="Poor match",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

        mock_db.search_memories.return_value = [
            (mem1, 0.1),
            (mem2, 0.95),
        ]  # 0.95 distance = 0.05 similarity
        mock_db.search_fts.return_value = []

        result = search_memories("test", mode="vector", limit=5, min_score=0.5)

        # Only mem1 should pass (similarity 0.9 > 0.5)
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "mem1"

    @patch("gmemory.commands.search.get_container")
    def test_recency_weight_boosts_recent(self, mock_get_container, mock_container):
        """Recency weight should boost recent memories."""
        container, mock_db, mock_embedder, mock_config = mock_container
        mock_get_container.return_value = container

        now = int(time.time())
        old_time = now - (60 * 24 * 3600)  # 60 days ago

        mem_old = Memory(
            id="old", content="Old memory", created_at=old_time, updated_at=old_time
        )
        mem_new = Memory(id="new", content="New memory", created_at=now, updated_at=now)

        # Both have same vector similarity
        mock_db.search_memories.return_value = [(mem_old, 0.1), (mem_new, 0.1)]
        mock_db.search_fts.return_value = []

        result = search_memories("memory", mode="vector", limit=5, recency_weight=0.5)

        # New memory should rank higher due to recency boost
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "new"


class TestFilterAndFormat:
    """Tests for _filter_and_format function."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        mock = MagicMock()
        mock.search_recency_window_days = 90
        return mock

    def test_excludes_superseded_by_default(self, mock_config):
        """Should exclude superseded memories by default."""
        now = int(time.time())
        mem1 = Memory(id="mem1", content="Active", created_at=now, updated_at=now)
        mem2 = Memory(
            id="mem2",
            content="Superseded",
            created_at=now,
            updated_at=now,
            superseded_by="mem3",
        )

        candidates = [
            {
                "memory": mem1,
                "vec_score": 0.9,
                "fts_score": 0.0,
                "combined_score": 0.9,
                "hit_sources": ["vector"],
            },
            {
                "memory": mem2,
                "vec_score": 0.8,
                "fts_score": 0.0,
                "combined_score": 0.8,
                "hit_sources": ["vector"],
            },
        ]

        results = _filter_and_format(candidates, mock_config, None, None, 10, False)

        assert len(results) == 1
        assert results[0]["id"] == "mem1"

    def test_includes_superseded_when_requested(self, mock_config):
        """Should include superseded memories when include_superseded=True."""
        now = int(time.time())
        mem1 = Memory(id="mem1", content="Active", created_at=now, updated_at=now)
        mem2 = Memory(
            id="mem2",
            content="Superseded",
            created_at=now,
            updated_at=now,
            superseded_by="mem3",
        )

        candidates = [
            {
                "memory": mem1,
                "vec_score": 0.9,
                "fts_score": 0.0,
                "combined_score": 0.9,
                "hit_sources": ["vector"],
            },
            {
                "memory": mem2,
                "vec_score": 0.8,
                "fts_score": 0.0,
                "combined_score": 0.8,
                "hit_sources": ["vector"],
            },
        ]

        results = _filter_and_format(
            candidates, mock_config, None, None, 10, False, include_superseded=True
        )

        assert len(results) == 2

    def test_respects_limit(self, mock_config):
        """Should respect the limit parameter."""
        now = int(time.time())
        candidates = []
        for i in range(10):
            mem = Memory(
                id=f"mem{i}", content=f"Content {i}", created_at=now, updated_at=now
            )
            candidates.append(
                {
                    "memory": mem,
                    "vec_score": 0.9 - i * 0.05,
                    "fts_score": 0.0,
                    "combined_score": 0.9 - i * 0.05,
                    "hit_sources": ["vector"],
                }
            )

        results = _filter_and_format(candidates, mock_config, None, None, 3, False)

        assert len(results) == 3

    def test_sorts_by_final_score(self, mock_config):
        """Should sort results by final score descending."""
        now = int(time.time())
        mem1 = Memory(id="low", content="Low score", created_at=now, updated_at=now)
        mem2 = Memory(id="high", content="High score", created_at=now, updated_at=now)

        candidates = [
            {
                "memory": mem1,
                "vec_score": 0.3,
                "fts_score": 0.0,
                "combined_score": 0.3,
                "hit_sources": ["vector"],
            },
            {
                "memory": mem2,
                "vec_score": 0.9,
                "fts_score": 0.0,
                "combined_score": 0.9,
                "hit_sources": ["vector"],
            },
        ]

        results = _filter_and_format(candidates, mock_config, None, None, 10, False)

        assert results[0]["id"] == "high"
        assert results[1]["id"] == "low"
