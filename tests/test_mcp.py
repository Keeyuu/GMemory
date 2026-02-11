"""Tests for GMemory MCP Server.

These tests verify the MCP tools work correctly with the underlying commands.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from typing import Any, Dict, List


class TestMCPToolsImport:
    """Test that MCP tools can be imported and registered."""

    def test_mcp_module_import(self) -> None:
        """MCP module should import without errors."""
        from gmemory.mcp import mcp, main

        assert mcp is not None
        assert main is not None

    def test_mcp_server_name(self) -> None:
        """MCP server should have correct name."""
        from gmemory.mcp import mcp

        assert mcp.name == "gmemory"


class TestSearchTools:
    """Test search-related MCP tools."""

    @patch("gmemory.mcp.tools.search.search_memories")
    def test_gmemory_search_basic(self, mock_search: MagicMock) -> None:
        """gmemory_search should call search_memories with correct params."""
        mock_search.return_value = {
            "results": [{"id": "test-id", "preview": "test content"}],
            "total": 1,
            "mode": "hybrid",
        }

        from gmemory.mcp.tools.search import register_search_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_search_tools(server)

        # Find the registered tool function
        # FastMCP stores tools in _tool_manager
        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_search":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(query="test query")
        result = json.loads(result_json)

        assert result["total"] == 1
        assert result["mode"] == "hybrid"
        mock_search.assert_called_once()

    @patch("gmemory.mcp.tools.search.quick_search")
    def test_gmemory_quick_search(self, mock_quick: MagicMock) -> None:
        """gmemory_quick_search should call quick_search."""
        mock_quick.return_value = {
            "results": [],
            "total": 0,
            "mode": "hybrid",
        }

        from gmemory.mcp.tools.search import register_search_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_search_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_quick_search":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(query="quick test")
        result = json.loads(result_json)

        assert result["total"] == 0
        mock_quick.assert_called_once_with(
            query="quick test",
            limit=5,
            recent_days=None,
        )

    @patch("gmemory.mcp.tools.search.search_memories")
    def test_gmemory_search_error_includes_error_envelope(
        self, mock_search: MagicMock
    ) -> None:
        """gmemory_search should return unified error envelope on failure."""
        mock_search.side_effect = RuntimeError("search failed")

        from gmemory.mcp.tools.search import register_search_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_search_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_search":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(query="test query")
        result = json.loads(result_json)

        assert result["ok"] is False
        assert result["error"] == "search failed"
        assert result["error_envelope"]["code"] == "INTERNAL"
        assert result["error_envelope"]["message"] == "search failed"


class TestCRUDTools:
    """Test CRUD-related MCP tools."""

    @patch("gmemory.mcp.tools.crud.get_memories")
    def test_gmemory_get(self, mock_get: MagicMock) -> None:
        """gmemory_get should parse comma-separated IDs."""
        mock_get.return_value = {
            "results": [{"id": "id1", "content": "test"}],
            "found": 1,
            "missing": ["id2"],
        }

        from gmemory.mcp.tools.crud import register_crud_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_crud_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_get":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(ids="id1, id2")
        result = json.loads(result_json)

        assert result["found"] == 1
        mock_get.assert_called_once_with(
            ids=["id1", "id2"],
            include_metadata=True,
        )

    @patch("gmemory.mcp.tools.crud.add_memory")
    def test_gmemory_add(self, mock_add: MagicMock) -> None:
        """gmemory_add should create a new memory."""
        mock_add.return_value = {
            "id": "new-id",
            "created": True,
            "embedding_stored": True,
            "preview": "Test content",
        }

        from gmemory.mcp.tools.crud import register_crud_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_crud_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_add":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(
            content="Test content",
            preview="Agent preview",
            tags="python,testing",
        )
        result = json.loads(result_json)

        assert result["created"] is True
        assert result["id"] == "new-id"
        assert result["preview"] == "Test content"
        mock_add.assert_called_once_with(
            content="Test content",
            preview="Agent preview",
            tags="python,testing",
            importance="medium",
            memory_type="observation",
            project_path=None,
            project_name=None,
            require_embedding=True,
        )

    @patch("gmemory.mcp.tools.crud.update_memory")
    def test_gmemory_update(self, mock_update: MagicMock) -> None:
        """gmemory_update should update existing memory."""
        mock_update.return_value = {
            "id": "test-id",
            "updated": True,
            "preview": "Updated content",
        }

        from gmemory.mcp.tools.crud import register_crud_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_crud_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_update":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(
            mem_id="test-id",
            content="Updated content",
            preview="Updated preview",
        )
        result = json.loads(result_json)

        assert result["updated"] is True
        assert result["preview"] == "Updated content"
        mock_update.assert_called_once_with(
            mem_id="test-id",
            content="Updated content",
            preview="Updated preview",
            tags=None,
            importance=None,
            memory_type=None,
            project_path=None,
            project_name=None,
            require_embedding=True,
        )

    @patch("gmemory.mcp.tools.crud.delete_memory")
    def test_gmemory_delete(self, mock_delete: MagicMock) -> None:
        """gmemory_delete should delete a memory."""
        mock_delete.return_value = {
            "id": "test-id",
            "deleted": True,
        }

        from gmemory.mcp.tools.crud import register_crud_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_crud_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_delete":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(mem_id="test-id")
        result = json.loads(result_json)

        assert result["deleted"] is True

    @patch("gmemory.mcp.tools.crud.delete_memory")
    def test_gmemory_delete_not_found(self, mock_delete: MagicMock) -> None:
        """gmemory_delete should handle not found error."""
        mock_delete.side_effect = ValueError("Memory not found")

        from gmemory.mcp.tools.crud import register_crud_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_crud_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_delete":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(mem_id="nonexistent")
        result = json.loads(result_json)

        assert result["deleted"] is False
        assert result["ok"] is False
        assert "error" in result
        assert result["error"] == "Memory not found"
        assert result["error_envelope"]["code"] == "VALIDATION_ERROR"
        assert result["error_envelope"]["message"] == "Memory not found"


class TestBrowseTools:
    """Test browse-related MCP tools."""

    @patch("gmemory.mcp.tools.browse.list_memories")
    def test_gmemory_list(self, mock_list: MagicMock) -> None:
        """gmemory_list should paginate memories."""
        mock_list.return_value = {
            "results": [{"id": "1", "preview": "test"}],
            "total": 100,
            "has_more": True,
        }

        from gmemory.mcp.tools.browse import register_browse_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_browse_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_list":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(limit=10, offset=0)
        result = json.loads(result_json)

        assert result["total"] == 100
        assert result["has_more"] is True

    @patch("gmemory.mcp.tools.browse.list_all_tags")
    def test_gmemory_tags(self, mock_tags: MagicMock) -> None:
        """gmemory_tags should list all tags."""
        mock_tags.return_value = {
            "tags": [{"tag": "python", "count": 10}],
            "total_unique": 5,
            "showing": 5,
        }

        from gmemory.mcp.tools.browse import register_browse_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_browse_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_tags":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func()
        result = json.loads(result_json)

        assert len(result["tags"]) == 1
        assert result["tags"][0]["tag"] == "python"

    @patch("gmemory.mcp.tools.browse.recent_memories")
    def test_gmemory_recent_keeps_memories_and_adds_results_alias(
        self, mock_recent: MagicMock
    ) -> None:
        """gmemory_recent should keep memories and expose results alias."""
        mock_recent.return_value = {
            "memories": [
                {
                    "id": "mem-1",
                    "content": "test",
                    "tags": ["mcp"],
                    "importance": "medium",
                    "created_at": 1,
                    "updated_at": 1,
                }
            ],
            "total": 1,
            "days": 7,
            "cutoff_timestamp": 123,
        }

        from gmemory.mcp.tools.browse import register_browse_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_browse_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_recent":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func()
        result = json.loads(result_json)

        assert len(result["memories"]) == 1
        assert len(result["results"]) == 1
        assert result["results"] == result["memories"]


class TestStatsTools:
    """Test stats-related MCP tools."""

    @patch("gmemory.mcp.tools.stats.get_stats")
    def test_gmemory_stats(self, mock_stats: MagicMock) -> None:
        """gmemory_stats should return system statistics."""
        mock_stats.return_value = {
            "total_memories": 100,
            "processed_sessions": 50,
            "unprocessed_sessions": 10,
        }

        from gmemory.mcp.tools.stats import register_stats_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_stats_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_stats":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func()
        result = json.loads(result_json)

        assert result["total_memories"] == 100

    @patch("gmemory.mcp.tools.stats.list_profiles")
    def test_gmemory_profiles(self, mock_profiles: MagicMock) -> None:
        """gmemory_profiles should list search profiles."""
        mock_profile = MagicMock()
        mock_profile.to_dict.return_value = {
            "name": "balanced",
            "mode": "hybrid",
            "recency_weight": 0.0,
        }
        mock_profiles.return_value = [mock_profile]

        from gmemory.mcp.tools.stats import register_stats_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_stats_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_profiles":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func()
        result = json.loads(result_json)

        assert len(result) == 1
        assert result[0]["name"] == "balanced"


class TestWorkflowTools:
    """Test workflow-related MCP tools."""

    @patch("gmemory.mcp.tools.workflow.fetch_unprocessed_sessions")
    def test_gmemory_session_list_defaults(self, mock_fetch: MagicMock) -> None:
        """gmemory_session_list should return unified backlog payload."""
        mock_fetch.return_value = {
            "sessions": [{"session_id": "ses-0", "agent": "opencode"}],
            "has_more": False,
            "remaining": 0,
            "total_pending": 0,
            "returned": 1,
            "remaining_after_page": 0,
            "offset": 0,
            "next_cursor": None,
        }

        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_session_list":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func()
        result = json.loads(result_json)

        assert result["state"] == "unprocessed"
        assert result["scope"] == "gmemory_backlog"
        mock_fetch.assert_called_once_with(
            limit=10,
            agent="all",
            scanner_type="all",
            offset=0,
            cursor=None,
            compact=True,
        )

    def test_gmemory_session_list_invalid_state(self) -> None:
        """gmemory_session_list should reject unsupported state values."""
        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_session_list":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(state="all")
        result = json.loads(result_json)

        assert result["ok"] is False
        assert result["error_envelope"]["code"] == "VALIDATION_ERROR"
        assert result["error_envelope"]["message"] == "state must be 'unprocessed'"
        assert result["error"]["code"] == "VALIDATION_ERROR"

    @patch("gmemory.mcp.tools.workflow.fetch_unprocessed_sessions")
    def test_gmemory_fetch_unprocessed_defaults(self, mock_fetch: MagicMock) -> None:
        """gmemory_fetch_unprocessed should call fetch with global defaults."""
        mock_fetch.return_value = {
            "sessions": [{"session_id": "ses-1", "agent": "opencode"}],
            "has_more": False,
            "remaining": 0,
            "total_pending": 0,
            "returned": 1,
            "remaining_after_page": 0,
            "offset": 0,
            "next_cursor": None,
        }

        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_fetch_unprocessed":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func()
        result = json.loads(result_json)

        assert result["has_more"] is False
        assert len(result["sessions"]) == 1
        assert "deprecated" in result
        mock_fetch.assert_called_once_with(
            limit=10,
            agent="all",
            scanner_type="all",
            offset=0,
            cursor=None,
            compact=True,
        )

    @patch("gmemory.mcp.tools.workflow.fetch_unprocessed_sessions")
    def test_gmemory_session_list_forwards_pagination_and_compact(
        self, mock_fetch: MagicMock
    ) -> None:
        """gmemory_session_list should forward offset/cursor/compact arguments."""
        mock_fetch.return_value = {
            "sessions": [],
            "has_more": False,
            "remaining": 0,
            "total_pending": 0,
            "returned": 0,
            "remaining_after_page": 0,
            "offset": 2,
            "next_cursor": None,
        }

        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_session_list":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(limit=5, offset=2, cursor="8", compact=False)
        result = json.loads(result_json)

        assert result["offset"] == 2
        mock_fetch.assert_called_once_with(
            limit=5,
            agent="all",
            scanner_type="all",
            offset=2,
            cursor="8",
            compact=False,
        )

    @patch("gmemory.mcp.tools.workflow.process_sessions")
    def test_gmemory_process_sessions_forwards_args(
        self, mock_process: MagicMock
    ) -> None:
        """gmemory_process_sessions should forward workflow parameters."""
        mock_process.return_value = {
            "sessions": [{"session_id": "ses-2", "agent": "opencode"}],
            "total": 1,
            "status": "pending",
            "workflow": {"commands": []},
        }

        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_process_sessions":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(
            limit=20,
            agent="opencode",
            scanner_type="all",
            auto_mark=False,
            show_backlog=False,
        )
        result = json.loads(result_json)

        assert result["total"] == 1
        assert result["status"] == "pending"
        mock_process.assert_called_once_with(
            limit=20,
            agent="opencode",
            scanner_type="all",
            auto_mark=False,
            show_backlog=False,
        )

    @patch("gmemory.mcp.tools.workflow.mark_session_versioned")
    def test_gmemory_mark_session_applied_or_noop(self, mock_mark: MagicMock) -> None:
        """gmemory_mark_session should return applied/noop result envelope."""
        mock_mark.return_value = {
            "result": "noop",
            "current_latest": {
                "session_id": "ses-1",
                "agent": "opencode",
                "source_updated_at": 100,
                "session_hash": "abc",
            },
        }

        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_mark_session":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(
            session_id="ses-1",
            agent="opencode",
            source_updated_at=100,
            session_hash="abc",
            idempotency_key="key-1",
        )
        result = json.loads(result_json)

        assert result["ok"] is True
        assert result["result"] == "noop"

    @patch("gmemory.mcp.tools.workflow.mark_session_versioned")
    def test_gmemory_mark_session_conflict(self, mock_mark: MagicMock) -> None:
        """gmemory_mark_session should map stale writes to CONFLICT."""
        mock_mark.return_value = {
            "result": "conflict",
            "current_latest": {
                "session_id": "ses-1",
                "agent": "opencode",
                "source_updated_at": 200,
                "session_hash": "new",
            },
        }

        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_mark_session":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(
            session_id="ses-1",
            agent="opencode",
            source_updated_at=100,
            session_hash="old",
            idempotency_key="key-2",
        )
        result = json.loads(result_json)

        assert result["ok"] is False
        assert result["error_envelope"]["code"] == "CONFLICT"
        assert result["error"]["code"] == "CONFLICT"
        assert "current_latest" in result["error"]["details"]

    @patch("gmemory.mcp.tools.workflow.batch_get_processed_status")
    def test_gmemory_get_processed_status_batch(self, mock_batch: MagicMock) -> None:
        """gmemory_get_processed_status should support batch with needs_reprocess."""
        mock_batch.return_value = [
            {
                "session_id": "ses-1",
                "agent": "opencode",
                "source_updated_at": 100,
                "session_hash": "aaa",
                "processor": "default",
                "latest": {
                    "session_id": "ses-1",
                    "agent": "opencode",
                    "source_updated_at": 100,
                    "session_hash": "aaa",
                },
                "needs_reprocess": True,
            },
            {
                "session_id": "ses-2",
                "agent": "opencode",
                "processor": "default",
                "latest": None,
                "needs_reprocess": True,
            },
        ]

        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_get_processed_status":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(
            items_json=json.dumps(
                [
                    {
                        "session_id": "ses-1",
                        "agent": "opencode",
                        "source_updated_at": 101,
                        "session_hash": "bbb",
                    },
                    {
                        "session_id": "ses-2",
                        "agent": "opencode",
                        "source_updated_at": 1,
                        "session_hash": "ccc",
                    },
                ]
            )
        )
        result = json.loads(result_json)

        assert result["ok"] is True
        assert result["count"] == 2
        assert result["total"] == 2
        assert result["results"][0]["needs_reprocess"] is True
        assert result["results"][1]["needs_reprocess"] is True

    @patch("gmemory.mcp.tools.workflow.batch_get_processed_status")
    def test_gmemory_get_processed_status_fallback_to_processed_at(
        self, mock_batch: MagicMock
    ) -> None:
        """When version fields are absent, processed_at should gate reprocess."""
        mock_batch.return_value = [
            {
                "session_id": "ses-old",
                "agent": "opencode",
                "processor": "default",
                "latest": {
                    "session_id": "ses-old",
                    "agent": "opencode",
                    "processed_at": 200,
                    "source_updated_at": None,
                    "session_hash": None,
                },
                "needs_reprocess": False,
            },
            {
                "session_id": "ses-new",
                "agent": "opencode",
                "processor": "default",
                "latest": {
                    "session_id": "ses-new",
                    "agent": "opencode",
                    "processed_at": 200,
                    "source_updated_at": None,
                    "session_hash": None,
                },
                "needs_reprocess": True,
            },
        ]

        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        tool_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_get_processed_status":
                tool_func = tool.fn
                break

        assert tool_func is not None
        result_json = tool_func(
            items_json=json.dumps(
                [
                    {
                        "session_id": "ses-old",
                        "agent": "opencode",
                        "source_updated_at": 150,
                    },
                    {
                        "session_id": "ses-new",
                        "agent": "opencode",
                        "source_updated_at": 250,
                    },
                ]
            )
        )
        result = json.loads(result_json)

        assert result["ok"] is True
        assert result["count"] == 2
        assert result["total"] == 2
        assert result["results"][0]["needs_reprocess"] is False
        assert result["results"][1]["needs_reprocess"] is True

    @patch("gmemory.mcp.tools.workflow.batch_get_processed_status")
    @patch("gmemory.mcp.tools.workflow.mark_session_versioned")
    def test_workflow_full_loop_reprocess_status_transition(
        self,
        mock_mark: MagicMock,
        mock_batch: MagicMock,
    ) -> None:
        """Full loop: mark v1 -> clean, source update -> reprocess, mark v2 -> clean."""
        mock_mark.side_effect = [
            {
                "result": "applied",
                "current_latest": {
                    "session_id": "ses-loop",
                    "agent": "opencode",
                    "source_updated_at": 100,
                    "session_hash": "h1",
                },
            },
            {
                "result": "applied",
                "current_latest": {
                    "session_id": "ses-loop",
                    "agent": "opencode",
                    "source_updated_at": 101,
                    "session_hash": "h2",
                },
            },
        ]
        mock_batch.side_effect = [
            [
                {
                    "session_id": "ses-loop",
                    "agent": "opencode",
                    "processor": "default",
                    "latest": {
                        "session_id": "ses-loop",
                        "agent": "opencode",
                        "source_updated_at": 100,
                        "session_hash": "h1",
                    },
                    "needs_reprocess": False,
                }
            ],
            [
                {
                    "session_id": "ses-loop",
                    "agent": "opencode",
                    "processor": "default",
                    "latest": {
                        "session_id": "ses-loop",
                        "agent": "opencode",
                        "source_updated_at": 100,
                        "session_hash": "h1",
                    },
                    "needs_reprocess": True,
                }
            ],
            [
                {
                    "session_id": "ses-loop",
                    "agent": "opencode",
                    "processor": "default",
                    "latest": {
                        "session_id": "ses-loop",
                        "agent": "opencode",
                        "source_updated_at": 101,
                        "session_hash": "h2",
                    },
                    "needs_reprocess": False,
                }
            ],
        ]

        from gmemory.mcp.tools.workflow import register_workflow_tools
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(name="test")
        register_workflow_tools(server)

        mark_func = None
        status_func = None
        for tool in server._tool_manager._tools.values():
            if tool.name == "gmemory_mark_session":
                mark_func = tool.fn
            if tool.name == "gmemory_get_processed_status":
                status_func = tool.fn

        assert mark_func is not None
        assert status_func is not None

        first_mark = json.loads(
            mark_func(
                session_id="ses-loop",
                agent="opencode",
                source_updated_at=100,
                session_hash="h1",
                idempotency_key="loop-1",
            )
        )
        assert first_mark["ok"] is True
        assert first_mark["result"] == "applied"

        first_status = json.loads(
            status_func(
                items_json=json.dumps(
                    [
                        {
                            "session_id": "ses-loop",
                            "agent": "opencode",
                            "source_updated_at": 100,
                            "session_hash": "h1",
                        }
                    ]
                )
            )
        )
        assert first_status["results"][0]["needs_reprocess"] is False

        updated_status = json.loads(
            status_func(
                items_json=json.dumps(
                    [
                        {
                            "session_id": "ses-loop",
                            "agent": "opencode",
                            "source_updated_at": 101,
                            "session_hash": "h2",
                        }
                    ]
                )
            )
        )
        assert updated_status["results"][0]["needs_reprocess"] is True

        second_mark = json.loads(
            mark_func(
                session_id="ses-loop",
                agent="opencode",
                source_updated_at=101,
                session_hash="h2",
                idempotency_key="loop-2",
            )
        )
        assert second_mark["ok"] is True
        assert second_mark["result"] == "applied"

        final_status = json.loads(
            status_func(
                items_json=json.dumps(
                    [
                        {
                            "session_id": "ses-loop",
                            "agent": "opencode",
                            "source_updated_at": 101,
                            "session_hash": "h2",
                        }
                    ]
                )
            )
        )
        assert final_status["results"][0]["needs_reprocess"] is False
