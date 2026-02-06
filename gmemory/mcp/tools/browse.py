"""MCP tools for GMemory browse operations.

This module exposes tools for browsing and listing memories.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from mcp.types import ToolAnnotations

from gmemory.commands.list import list_memories
from gmemory.commands.quick import (
    recent_memories,
    today_summary,
    find_by_tag,
    list_all_tags,
)


def register_browse_tools(server: Any) -> None:
    """Register browse tools on the MCP server.

    Tools:
        gmemory_list: Paginated memory listing.
        gmemory_recent: Recent memories from last N days.
        gmemory_today: Today's activity summary.
        gmemory_tags: List all tags with counts.
        gmemory_tag: Find memories by tag.
    """

    @server.tool(
        name="gmemory_list",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_list(
        limit: int = 20,
        offset: int = 0,
        project_path: Optional[str] = None,
        importance: Optional[str] = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> str:
        """分页浏览记忆列表。

        不需要搜索查询，适合浏览概览。

        Args:
            limit: 每页数量 (默认 20)
            offset: 跳过的记录数 (用于分页)
            project_path: 按项目路径过滤
            importance: 按重要程度过滤 (high/medium/low)
            sort_by: 排序字段 (created_at/updated_at)
            sort_order: 排序方向 (asc/desc)

        返回结构 (JSON):
            {
                "results": [
                    {"id": "...", "tags": [...], "preview": "...", "importance": "high", ...}
                ],
                "total": N,
                "has_more": true/false
            }
        """
        result = list_memories(
            limit=limit,
            offset=offset,
            project_path=project_path,
            importance=importance,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @server.tool(
        name="gmemory_recent",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_recent(
        days: int = 7,
        limit: int = 10,
        project_path: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> str:
        """获取最近 N 天的记忆。

        Args:
            days: 回溯天数 (默认 7)
            limit: 返回数量上限 (默认 10)
            project_path: 按项目路径过滤
            tags: 按标签过滤，逗号分隔

        返回结构 (JSON):
            {
                "memories": [...],
                "total": N,
                "days": 7,
                "cutoff_timestamp": 1234567890
            }
        """
        # Parse tags if provided
        tags_list = None
        if tags:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]

        result = recent_memories(
            days=days,
            limit=limit,
            project_path=project_path,
            tags=tags_list,
        )

        # Convert Memory objects to dicts for JSON serialization
        if result.get("memories"):
            memories_data = []
            for mem in result["memories"]:
                if hasattr(mem, "id"):
                    memories_data.append(
                        {
                            "id": mem.id,
                            "content": mem.content,
                            "tags": mem.tags,
                            "importance": mem.importance,
                            "created_at": mem.created_at,
                            "updated_at": mem.updated_at,
                        }
                    )
                else:
                    memories_data.append(mem)
            result["memories"] = memories_data

        return json.dumps(result, ensure_ascii=False, default=str)

    @server.tool(
        name="gmemory_today",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_today() -> str:
        """获取今日活动统计。

        返回结构 (JSON):
            {
                "memories_created": N,
                "memories_updated": N,
                "sessions_processed": N,
                "top_tags": [...]
            }
        """
        result = today_summary()
        return json.dumps(result, ensure_ascii=False, default=str)

    @server.tool(
        name="gmemory_tags",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_tags(limit: int = 50) -> str:
        """列出所有标签及其使用次数。

        Args:
            limit: 返回标签数量上限 (默认 50)

        返回结构 (JSON):
            {
                "tags": [
                    {"tag": "python", "count": 42},
                    {"tag": "api", "count": 28},
                    ...
                ],
                "total_unique": N,
                "showing": N
            }
        """
        result = list_all_tags(limit=limit)
        return json.dumps(result, ensure_ascii=False, default=str)

    @server.tool(
        name="gmemory_tag",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_tag(
        tag: str,
        limit: int = 20,
        compact: bool = True,
    ) -> str:
        """按标签查找记忆。

        Args:
            tag: 要查找的标签名
            limit: 返回数量上限 (默认 20)
            compact: True 返回精简预览

        返回结构 (JSON):
            {
                "tag": "python",
                "memories": [...],
                "total": N
            }
        """
        result = find_by_tag(
            tag=tag,
            limit=limit,
            compact=compact,
        )
        return json.dumps(result, ensure_ascii=False, default=str)
