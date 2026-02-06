"""GMemory MCP Server module.

This module provides a Model Context Protocol (MCP) server for GMemory,
allowing AI agents to interact with the memory system through standardized tools.
"""

from gmemory.mcp.server import mcp, main

__all__ = ["mcp", "main"]
