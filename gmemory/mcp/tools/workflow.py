"""MCP tools for session processing workflow state."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

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

    if incoming_updated is None and incoming_hash is None:
        return False

    if incoming_updated is not None and latest_updated is not None:
        if int(incoming_updated) > int(latest_updated):
            return True
        if int(incoming_updated) < int(latest_updated):
            return False

    if incoming_hash is not None and latest_hash is not None:
        return str(incoming_hash) != str(latest_hash)

    if incoming_hash is not None and latest_hash is None:
        return True

    return False


def register_workflow_tools(server: Any) -> None:
    """Register workflow state tools on the MCP server."""

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
