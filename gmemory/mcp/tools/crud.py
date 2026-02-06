"""MCP tools for GMemory CRUD operations.

This module exposes tools for creating, reading, updating, and deleting memories.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from mcp.types import ToolAnnotations

from gmemory.commands.get import get_memories
from gmemory.commands.add import add_memory
from gmemory.commands.update import update_memory
from gmemory.commands.delete import delete_memory


def register_crud_tools(server: Any) -> None:
    """Register CRUD tools on the MCP server.

    Tools:
        gmemory_get: Get full memory content by ID(s).
        gmemory_add: Add a new memory.
        gmemory_update: Update an existing memory.
        gmemory_delete: Delete a memory.
    """

    @server.tool(
        name="gmemory_get",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_get(
        ids: str,
        include_metadata: bool = True,
    ) -> str:
        """按 ID 获取记忆的完整内容。

        这是渐进式披露的第二层：
        1. search --compact → 获取 ID 和预览
        2. get <ids> → 获取完整内容

        Args:
            ids: 记忆 ID，多个用逗号分隔 (如 "id1,id2,id3")
            include_metadata: True 包含元数据 (项目、代理、时间戳等)

        返回结构 (JSON):
            {
                "results": [
                    {
                        "id": "...",
                        "content": "完整内容...",
                        "tags": [...],
                        "importance": "high",
                        ...
                    }
                ],
                "found": N,
                "missing": ["id_not_found"] or null
            }
        """
        # Parse comma-separated IDs
        id_list = [id.strip() for id in ids.split(",") if id.strip()]
        if not id_list:
            return json.dumps({"results": [], "found": 0, "missing": None})

        result = get_memories(ids=id_list, include_metadata=include_metadata)
        return json.dumps(result, ensure_ascii=False, default=str)

    @server.tool(
        name="gmemory_add",
        annotations=ToolAnnotations(readOnlyHint=False),
    )
    def gmemory_add(
        content: str,
        tags: str,
        importance: str = "medium",
        memory_type: str = "observation",
        project_path: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> str:
        """添加新记忆到知识库。

        Args:
            content: 记忆内容文本
            tags: 标签，逗号分隔 (如 "python,api,design-pattern")
            importance: 重要程度 (low/medium/high)，默认 medium
            memory_type: 记忆类型 (observation/fact/pattern)，默认 observation
            project_path: 关联的项目路径
            project_name: 关联的项目名称

        返回结构 (JSON):
            {
                "id": "新记忆的ID",
                "created": true,
                "embedding_stored": true
            }
        """
        try:
            result = add_memory(
                content=content,
                tags=tags,
                importance=importance,
                memory_type=memory_type,
                project_path=project_path,
                project_name=project_name,
                require_embedding=True,
            )
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps(
                {
                    "id": None,
                    "created": False,
                    "error": str(e),
                }
            )

    @server.tool(
        name="gmemory_update",
        annotations=ToolAnnotations(readOnlyHint=False),
    )
    def gmemory_update(
        mem_id: str,
        content: Optional[str] = None,
        tags: Optional[str] = None,
        importance: Optional[str] = None,
        memory_type: Optional[str] = None,
        project_path: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> str:
        """更新现有记忆。

        只需提供要更新的字段，未提供的字段保持不变。

        Args:
            mem_id: 要更新的记忆 ID
            content: 新的内容 (可选)
            tags: 新的标签，逗号分隔 (可选)
            importance: 新的重要程度 (可选)
            memory_type: 新的类型 (可选)
            project_path: 新的项目路径 (可选)
            project_name: 新的项目名称 (可选)

        返回结构 (JSON):
            {
                "id": "记忆ID",
                "updated": true
            }
        """
        try:
            result = update_memory(
                mem_id=mem_id,
                content=content,
                tags=tags,
                importance=importance,
                memory_type=memory_type,
                project_path=project_path,
                project_name=project_name,
                require_embedding=True,
            )
            return json.dumps(result, ensure_ascii=False, default=str)
        except ValueError as e:
            return json.dumps(
                {
                    "id": mem_id,
                    "updated": False,
                    "error": str(e),
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "id": mem_id,
                    "updated": False,
                    "error": str(e),
                }
            )

    @server.tool(
        name="gmemory_delete",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    def gmemory_delete(mem_id: str) -> str:
        """删除指定记忆。

        注意：删除操作不可恢复。

        Args:
            mem_id: 要删除的记忆 ID

        返回结构 (JSON):
            {
                "id": "记忆ID",
                "deleted": true
            }
        """
        try:
            result = delete_memory(mem_id=mem_id)
            return json.dumps(result, ensure_ascii=False, default=str)
        except ValueError as e:
            return json.dumps(
                {
                    "id": mem_id,
                    "deleted": False,
                    "error": str(e),
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "id": mem_id,
                    "deleted": False,
                    "error": str(e),
                }
            )
