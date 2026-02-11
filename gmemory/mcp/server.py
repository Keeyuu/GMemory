"""GMemory MCP Server.

This module implements a FastMCP-based MCP server that exposes GMemory
functionality through standardized MCP tools.

Tools are organized by category:
- Search: gmemory_search, gmemory_quick_search
- CRUD: gmemory_get, gmemory_add, gmemory_update, gmemory_delete
- Browse: gmemory_list, gmemory_recent, gmemory_today, gmemory_tags, gmemory_tag
- Stats: gmemory_stats, gmemory_profiles
"""

from __future__ import annotations

import json
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from gmemory.mcp.tools import register_stats_tools
from gmemory.mcp.tools.search import register_search_tools
from gmemory.mcp.tools.crud import register_crud_tools
from gmemory.mcp.tools.browse import register_browse_tools
from gmemory.mcp.tools.workflow import register_workflow_tools

# Create the MCP server instance
mcp = FastMCP(
    name="gmemory",
)

# Register all tool categories
register_search_tools(mcp)
register_crud_tools(mcp)
register_browse_tools(mcp)
register_stats_tools(mcp)
register_workflow_tools(mcp)


def main() -> None:
    """Run the MCP server with stdio transport."""
    mcp.run()


def streamable_http_app(path: Optional[str] = None) -> Any:
    """Build Streamable HTTP app with optional route path override."""
    if path is None:
        return mcp.streamable_http_app()

    original_path = mcp.settings.streamable_http_path
    try:
        mcp.settings.streamable_http_path = path
        return mcp.streamable_http_app()
    finally:
        mcp.settings.streamable_http_path = original_path


if __name__ == "__main__":
    main()
