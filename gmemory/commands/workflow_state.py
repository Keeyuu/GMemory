"""Workflow state commands for versioned session processing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from gmemory.container import get_container


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


def mark_session_versioned(
    *,
    session_id: str,
    agent: str,
    status: str = "processed",
    reason: Optional[str] = None,
    source_updated_at: Optional[int] = None,
    session_hash: Optional[str] = None,
    processor: str = "default",
    run_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Mark one session with version-aware idempotent semantics."""
    container = get_container()
    db: Any = container.get_database()
    return db.mark_session_processed_versioned(
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


def batch_get_processed_status(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Query latest processed-state in batch and compute needs_reprocess."""
    container = get_container()
    db: Any = container.get_database()

    rows = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each item must be an object")

        session_id = item.get("session_id")
        agent = item.get("agent")
        processor = item.get("processor", "default")
        if not session_id or not agent:
            raise ValueError("each item requires session_id and agent")

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
    return rows
