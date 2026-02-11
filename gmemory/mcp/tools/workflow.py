"""MCP tools for session processing workflow state."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

from gmemory.commands.fetch import fetch_unprocessed_sessions
from gmemory.commands.workflow import process_sessions
from gmemory.storage.database import MemoryDatabase


def _error(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> str:
    payload: Dict[str, Any] = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        payload["error"]["details"] = details
    return json.dumps(payload, ensure_ascii=False, default=str)


def _needs_reprocess(latest: Optional[Dict[str, Any]], item: Dict[str, Any]) -> bool:
    if latest is None:
        return True

    incoming_updated = item.get("source_updated_at")
    latest_updated = latest.get("source_updated_at")
    incoming_hash = item.get("session_hash")
    latest_hash = latest.get("session_hash")
    latest_processed = latest.get("processed_at")

    latest_processed_int = (
        int(latest_processed) if latest_processed is not None else None
    )
    latest_updated_int = int(latest_updated) if latest_updated is not None else None
    incoming_updated_int = (
        int(incoming_updated) if incoming_updated is not None else None
    )

    if incoming_updated is None and incoming_hash is None:
        return False

    if latest_updated_int is None and latest_hash is None:
        if incoming_updated_int is None:
            return False
        if latest_processed_int is None:
            return False
        return incoming_updated_int > latest_processed_int

    if incoming_updated_int is not None and latest_updated_int is not None:
        if incoming_updated_int > latest_updated_int:
            return True
        if incoming_updated_int < latest_updated_int:
            return False

    if incoming_updated_int is not None and latest_updated_int is None:
        if latest_processed_int is None:
            return True
        return incoming_updated_int > latest_processed_int

    if incoming_hash is not None and latest_hash is not None:
        return str(incoming_hash) != str(latest_hash)

    if incoming_hash is not None and latest_hash is None:
        return True

    return False


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
            return json.dumps(result, ensure_ascii=False, default=str)
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
            return json.dumps(result, ensure_ascii=False, default=str)
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
            return json.dumps(result, ensure_ascii=False, default=str)
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

        db = MemoryDatabase()
        try:
            result = db.mark_session_processed_versioned(
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

            return json.dumps(
                {
                    "ok": True,
                    "result": result.get("result", "applied"),
                    "session_id": session_id,
                    "agent": agent,
                    "current_latest": result.get("current_latest"),
                },
                ensure_ascii=False,
                default=str,
            )
        except Exception as exc:  # pragma: no cover - defensive
            return _error("INTERNAL", str(exc))
        finally:
            db.close()

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

        db = MemoryDatabase()
        try:
            rows = []
            for item in items:
                if not isinstance(item, dict):
                    return _error(
                        "VALIDATION_ERROR",
                        "each item must be an object",
                    )

                session_id = item.get("session_id")
                agent = item.get("agent")
                processor = item.get("processor", "default")
                if not session_id or not agent:
                    return _error(
                        "VALIDATION_ERROR",
                        "each item requires session_id and agent",
                    )

                latest = db.get_latest_processed_session(
                    agent=agent,
                    session_id=session_id,
                    processor=processor,
                    any_agent=True,
                )
                rows.append(
                    {
                        "session_id": session_id,
                        "agent": agent,
                        "processor": processor,
                        "latest": latest,
                        "needs_reprocess": _needs_reprocess(latest, item),
                    }
                )

            return json.dumps(
                {
                    "ok": True,
                    "results": rows,
                    "count": len(rows),
                },
                ensure_ascii=False,
                default=str,
            )
        except Exception as exc:  # pragma: no cover - defensive
            return _error("INTERNAL", str(exc))
        finally:
            db.close()
