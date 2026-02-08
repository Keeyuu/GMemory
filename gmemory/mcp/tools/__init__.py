"""MCP tools package for GMemory."""

from gmemory.mcp.tools.stats import register_stats_tools
from gmemory.mcp.tools.search import register_search_tools
from gmemory.mcp.tools.crud import register_crud_tools
from gmemory.mcp.tools.browse import register_browse_tools
from gmemory.mcp.tools.workflow import register_workflow_tools

__all__ = [
    "register_stats_tools",
    "register_search_tools",
    "register_crud_tools",
    "register_browse_tools",
    "register_workflow_tools",
]
