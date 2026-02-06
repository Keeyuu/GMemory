"""MCP tools for GMemory search operations.

This module exposes search tools for semantic and FTS search.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from mcp.types import ToolAnnotations

from gmemory.commands.search import search_memories
from gmemory.commands.quick import quick_search


def register_search_tools(server: Any) -> None:
    """Register search tools on the MCP server.

    Tools:
        gmemory_search: Full-featured hybrid/vector/FTS search.
        gmemory_quick_search: Quick compact search for fast lookups.
    """

    @server.tool(
        name="gmemory_search",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_search(
        query: str,
        mode: str = "hybrid",
        limit: int = 10,
        compact: bool = True,
        project_path: Optional[str] = None,
        tags: Optional[str] = None,
        recency_weight: float = 0.0,
        profile: Optional[str] = None,
        explain: bool = False,
        min_score: float = 0.2,
    ) -> str:
        """搜索记忆库。

        支持三种搜索模式：
        - hybrid: 向量语义搜索 + 全文搜索融合 (默认，推荐)
        - vector: 纯向量语义搜索
        - fts: 纯全文关键词搜索

        Args:
            query: 搜索查询文本
            mode: 搜索模式 (hybrid/vector/fts)
            limit: 返回结果数量上限
            compact: True 返回精简预览，False 返回完整内容
            project_path: 按项目路径过滤
            tags: 按标签过滤，逗号分隔 (如 "python,api")
            recency_weight: 时间衰减权重 (0.0-1.0)，越高越偏向最近的记忆
            profile: 使用预设的搜索配置 (balanced/semantic/keyword/recent/very-recent)
            explain: True 返回评分详情
            min_score: 最低相关度阈值 (0.0-1.0)

        返回结构 (JSON):
            {
                "results": [...],  # 搜索结果列表
                "total": N,        # 结果数量
                "mode": "hybrid",  # 使用的搜索模式
                "profile": "...",  # 使用的配置名称 (如有)
            }
        """
        result = search_memories(
            query=query,
            mode=mode,
            limit=limit,
            compact=compact,
            project_path=project_path,
            tags=tags,
            recency_weight=recency_weight,
            profile=profile,
            explain=explain,
            min_score=min_score,
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @server.tool(
        name="gmemory_quick_search",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_quick_search(
        query: str,
        limit: int = 5,
        recent_days: Optional[int] = None,
    ) -> str:
        """快速搜索记忆 (精简模式)。

        为快速查询优化的简化搜索接口：
        - 默认使用 hybrid 模式和 compact 输出
        - 适合快速查找和上下文检索

        Args:
            query: 搜索查询文本
            limit: 返回结果数量 (默认 5)
            recent_days: 可选，优先返回最近 N 天的记忆

        返回结构 (JSON):
            {
                "results": [
                    {"id": "...", "tags": [...], "preview": "...", "score": 0.85},
                    ...
                ],
                "total": N,
                "mode": "hybrid"
            }
        """
        result = quick_search(
            query=query,
            limit=limit,
            recent_days=recent_days,
        )
        return json.dumps(result, ensure_ascii=False, default=str)
