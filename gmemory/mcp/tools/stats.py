"""MCP tools for GMemory stats and profiles.

This module exposes read-only tools for system statistics and search profiles.
Each tool returns a JSON string for client-side consumption.
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from gmemory.commands.profiles import list_profiles
from gmemory.commands.stats import get_stats
from gmemory.mcp.response import dumps_json, error_json


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

        try:
            stats: dict[str, Any] = get_stats()
            return dumps_json(stats)
        except Exception as exc:  # pragma: no cover - defensive
            return error_json("INTERNAL", str(exc), error_mode="string")

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

        try:
            profiles = [profile.to_dict() for profile in list_profiles()]
            return dumps_json(profiles)
        except Exception as exc:  # pragma: no cover - defensive
            return error_json("INTERNAL", str(exc), error_mode="string")
