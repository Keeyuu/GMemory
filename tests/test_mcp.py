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
        assert "error" in result


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
