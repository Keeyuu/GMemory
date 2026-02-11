"""MCP tools for session processing workflow state."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

from gmemory.commands.fetch import fetch_unprocessed_sessions
from gmemory.commands.workflow import process_sessions
from gmemory.commands.workflow_state import (
    batch_get_processed_status,
    mark_session_versioned,
)
from gmemory.mcp.response import dumps_json, error_json


def _error(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> str:
    return error_json(
        code=code,
        message=message,
        details=details,
        error_mode="object",
    )


def register_workflow_tools(server: Any) -> None:
    """Register workflow state tools on the MCP server."""

    def _list_unprocessed_sessions(
        limit: int,
        agent: str,
        scanner_type: str,
    ) -> Dict[str, Any]:
        resolved_agent = (agent or "all").strip() or "all"
        resolved_scanner = (scanner_type or "all").strip() or "all"
        return fetch_unprocessed_sessions(
            limit=limit,
            agent=resolved_agent,
            scanner_type=resolved_scanner,
        )

    @server.tool(
        name="gmemory_session_list",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_session_list(
        limit: int = 10,
        state: str = "unprocessed",
        agent: str = "all",
        scanner_type: str = "all",
    ) -> str:
        """列出会话队列（统一入口）。

        Args:
            limit: 返回会话数量上限。
            state: 队列状态（当前仅支持 unprocessed）。
            agent: agent 过滤（默认 all）。
            scanner_type: 扫描器类型（默认 all，表示聚合全部 scanner）。

        返回结构 (JSON):
            {
                "sessions": [...],
                "has_more": true/false,
                "remaining": 0,
                "state": "unprocessed",
                "scope": "gmemory_backlog"
            }
        """
        if limit <= 0:
            return _error("VALIDATION_ERROR", "limit must be greater than 0")

        normalized_state = (state or "unprocessed").strip().lower()
        if normalized_state != "unprocessed":
            return _error(
                "VALIDATION_ERROR",
                "state must be 'unprocessed'",
            )

        try:
            result = _list_unprocessed_sessions(
                limit=limit,
                agent=agent,
                scanner_type=scanner_type,
            )
            result["state"] = "unprocessed"
            result["scope"] = "gmemory_backlog"
            return dumps_json(result)
        except Exception as exc:  # pragma: no cover - defensive
            return _error("INTERNAL", str(exc))

    @server.tool(
        name="gmemory_fetch_unprocessed",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_fetch_unprocessed(
        limit: int = 10,
        agent: str = "all",
        scanner_type: str = "all",
    ) -> str:
        """获取未处理会话列表（支持多 scanner 聚合）。

        Args:
            limit: 返回会话数量上限。
            agent: agent 过滤（默认 all）。
            scanner_type: 扫描器类型（默认 all，表示聚合全部 scanner）。

        返回结构 (JSON):
            {
                "sessions": [...],
                "has_more": true/false,
                "remaining": 0,
                "error": "..."  # 仅错误时存在
            }
        """
        if limit <= 0:
            return _error("VALIDATION_ERROR", "limit must be greater than 0")

        try:
            result = _list_unprocessed_sessions(
                limit=limit,
                agent=agent,
                scanner_type=scanner_type,
            )
            result["deprecated"] = "Use gmemory_session_list instead"
            return dumps_json(result)
        except Exception as exc:  # pragma: no cover - defensive
            return _error("INTERNAL", str(exc))

    @server.tool(
        name="gmemory_process_sessions",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_process_sessions(
        limit: int = 5,
        agent: str = "all",
        scanner_type: str = "all",
        auto_mark: bool = False,
        show_backlog: bool = True,
    ) -> str:
        """获取待处理会话并返回处理工作流建议。

        Args:
            limit: 返回会话数量上限。
            agent: agent 过滤（默认 all）。
            scanner_type: 扫描器类型（默认 all，表示聚合全部 scanner）。
            auto_mark: 是否自动标记（仅保留参数语义，由 commands 侧处理）。
            show_backlog: 是否返回 backlog 统计。

        返回结构 (JSON):
            {
                "sessions": [...],
                "total": 0,
                "backlog": {...},
                "workflow": {...},
                "hint": "...",
                "status": "pending|up_to_date"
            }
        """
        if limit <= 0:
            return _error("VALIDATION_ERROR", "limit must be greater than 0")

        resolved_agent = (agent or "all").strip() or "all"
        resolved_scanner = (scanner_type or "all").strip() or "all"

        try:
            result = process_sessions(
                limit=limit,
                agent=resolved_agent,
                scanner_type=resolved_scanner,
                auto_mark=auto_mark,
                show_backlog=show_backlog,
            )
            return dumps_json(result)
        except Exception as exc:  # pragma: no cover - defensive
            return _error("INTERNAL", str(exc))

    @server.tool(
        name="gmemory_mark_session",
        annotations=ToolAnnotations(readOnlyHint=False),
    )
    def gmemory_mark_session(
        session_id: str,
        agent: str,
        status: str = "processed",
        reason: Optional[str] = None,
        source_updated_at: Optional[int] = None,
        session_hash: Optional[str] = None,
        processor: str = "default",
        run_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """Mark one session with version-aware idempotent semantics."""
        if not session_id or not agent:
            return _error(
                "VALIDATION_ERROR",
                "session_id and agent are required",
            )

        try:
            result = mark_session_versioned(
                agent=agent,
                session_id=session_id,
                status=status,
                reason=reason,
                source_updated_at=source_updated_at,
                session_hash=session_hash,
                processor=processor,
                run_id=run_id,
                idempotency_key=idempotency_key,
            )

            if result.get("result") == "conflict":
                return _error(
                    "CONFLICT",
                    "stale session version rejected",
                    {"current_latest": result.get("current_latest")},
                )

            return dumps_json(
                {
                    "ok": True,
                    "result": result.get("result", "applied"),
                    "session_id": session_id,
                    "agent": agent,
                    "current_latest": result.get("current_latest"),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive
            return _error("INTERNAL", str(exc))

    @server.tool(
        name="gmemory_get_processed_status",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def gmemory_get_processed_status(items_json: str) -> str:
        """Batch query processed-state and compute needs_reprocess."""
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            return _error("VALIDATION_ERROR", "items_json must be valid JSON array")

        if not isinstance(items, list):
            return _error("VALIDATION_ERROR", "items_json must decode to a list")

        try:
            rows = batch_get_processed_status(items)

            return dumps_json(
                {
                    "ok": True,
                    "results": rows,
                    "count": len(rows),
                    "total": len(rows),
                },
            )
        except ValueError as exc:
            return _error("VALIDATION_ERROR", str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            return _error("INTERNAL", str(exc))
