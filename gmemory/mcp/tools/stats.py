"""MCP tools for GMemory stats and profiles.

This module exposes read-only tools for system statistics and search profiles.
Each tool returns a JSON string for client-side consumption.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.types import ToolAnnotations

from gmemory.commands.profiles import list_profiles
from gmemory.commands.stats import get_stats


def register_stats_tools(server: Any) -> None:
    """Register stats and profiles tools on the MCP server.

    Tools:
        gmemory_stats: System statistics including counts and breakdowns.
        gmemory_profiles: Available search profile configurations.
    """

    @server.tool(
        name="gmemory_stats",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_stats() -> str:
        """获取系统统计信息。

        返回结构:
            JSON 字符串，字段包含:
            - total_memories
            - processed_sessions
            - unprocessed_sessions
            - scan_runs
            - scan_errors
            - by_project
            - by_importance
        """

        stats: dict[str, Any] = get_stats()
        return json.dumps(stats, ensure_ascii=False)

    @server.tool(
        name="gmemory_profiles",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_profiles() -> str:
        """列出搜索 profile 配置。

        返回结构:
            JSON 字符串，为 profile 列表，每个元素包含:
            - name
            - description
            - mode
            - recency_weight
            - use_tag_index
            - tag_weight
            - vector_weight
            - fts_weight
        """

        profiles = [profile.to_dict() for profile in list_profiles()]
        return json.dumps(profiles, ensure_ascii=False)
