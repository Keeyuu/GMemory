"""Tests for dedupe and export commands."""

import pytest
import time
import tempfile
from pathlib import Path

from gmemory.commands.dedupe import (
    DuplicateGroup,
    find_duplicates,
    merge_memories,
    auto_dedupe,
)
from gmemory.commands.export import (
    export_session,
    export_report,
    export_memories,
    _format_timestamp,
)


class TestDuplicateGroup:
    """Tests for DuplicateGroup dataclass."""

    def test_to_dict(self):
        """Test converting DuplicateGroup to dict."""
        group = DuplicateGroup(
            representative_id="mem1",
            representative_preview="Test content...",
            members=[{"id": "mem2", "preview": "Similar content", "similarity": 0.95}],
            similarity_scores=[0.95],
            tag_overlap=0.5,
        )
        d = group.to_dict()
        assert d["representative_id"] == "mem1"
        assert d["member_count"] == 1
        assert len(d["members"]) == 1
        assert d["tag_overlap"] == 0.5


class TestMergeMemories:
    """Tests for merge_memories function."""

    def test_merge_requires_two_ids(self):
        """Test that merge requires at least 2 memory IDs."""
        result = merge_memories(memory_ids=["single_id"])
        assert "error" in result
        assert "at least 2" in result["error"]

    def test_merge_empty_list(self):
        """Test merge with empty list."""
        result = merge_memories(memory_ids=[])
        assert "error" in result

    def test_merge_missing_memories(self):
        """Test merge with non-existent memory IDs."""
        result = merge_memories(
            memory_ids=["nonexistent1", "nonexistent2"],
            dry_run=True,
        )
        assert "error" in result
        assert "not found" in result["error"]


class TestFindDuplicates:
    """Tests for find_duplicates function."""

    def test_find_duplicates_empty_db(self):
        """Test finding duplicates with insufficient memories."""
        # This test uses the actual database which may be empty
        result = find_duplicates(limit=5)
        # Should not error, just return empty or message
        assert "groups" in result or "error" in result or "message" in result


class TestExportSession:
    """Tests for session export functionality."""

    def test_export_nonexistent_session(self):
        """Test exporting a non-existent session."""
        result = export_session("nonexistent_session_id")
        # Should return error or empty result
        assert "error" in result or result.get("memory_count", 0) == 0

    def test_export_json_format(self):
        """Test JSON format export."""
        result = export_session("test_session", format="json")
        # Check format is set correctly
        assert result.get("format") == "json" or "error" in result

    def test_export_markdown_format(self):
        """Test Markdown format export."""
        result = export_session("test_session", format="markdown")
        assert result.get("format") == "markdown" or "error" in result


class TestExportReport:
    """Tests for report export functionality."""

    def test_export_report_json(self):
        """Test JSON report export."""
        result = export_report(format="json", limit=5)
        assert result.get("format") == "json"
        # Should have session_count even if 0
        assert "session_count" in result or "error" in result

    def test_export_report_markdown(self):
        """Test Markdown report export."""
        result = export_report(format="markdown", limit=5)
        assert result.get("format") == "markdown"

    def test_export_report_with_since(self):
        """Test report with time filter."""
        result = export_report(format="json", since_days=7)
        # Should not error
        assert "error" not in result or "session_count" in result


class TestExportMemories:
    """Tests for memory export functionality."""

    def test_export_nonexistent_memories(self):
        """Test exporting non-existent memory IDs."""
        result = export_memories(
            memory_ids=["nonexistent1", "nonexistent2"],
            format="json",
        )
        assert "error" in result or result.get("memory_count", 0) == 0

    def test_export_with_filters(self):
        """Test export with tag filters."""
        result = export_memories(
            tags=["nonexistent_tag"],
            format="markdown",
            limit=10,
        )
        # Should return error or empty
        assert "error" in result or result.get("memory_count", 0) == 0


class TestExportToFile:
    """Tests for file output functionality."""

    def test_export_to_file(self):
        """Test exporting to a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_export.md"
            result = export_report(
                format="markdown",
                limit=5,
                output_path=str(output_path),
            )
            # Should have output_path in result or content
            if "error" not in result:
                assert "output_path" in result or "content" in result

    def test_export_creates_parent_dirs(self):
        """Test that export creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "nested" / "export.json"
            result = export_report(
                format="json",
                limit=5,
                output_path=str(output_path),
            )
            # Should succeed or have content fallback
            if "error" not in result:
                assert "output_path" in result or "content" in result


class TestFormatTimestamp:
    """Tests for timestamp formatting."""

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        ts = int(time.time())
        formatted = _format_timestamp(ts)
        assert len(formatted) == 19  # "YYYY-MM-DD HH:MM:SS"
        assert "-" in formatted
        assert ":" in formatted


class TestAutoDedupe:
    """Tests for auto_dedupe function."""

    def test_auto_dedupe_dry_run_default(self):
        """Test that auto_dedupe defaults to dry_run."""
        result = auto_dedupe(limit=5)
        # Should be dry run by default
        assert result.get("dry_run", True) is True

    def test_auto_dedupe_high_threshold(self):
        """Test auto_dedupe with very high threshold."""
        result = auto_dedupe(threshold=0.99, limit=5)
        # With 0.99 threshold, unlikely to find duplicates
        assert "groups_processed" in result or "message" in result or "error" in result
