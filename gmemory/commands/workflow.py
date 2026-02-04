"""Workflow command for GMemory - single command automation loop."""

import json
from typing import Any, Dict, List, Optional

from gmemory.commands.fetch import fetch_unprocessed_sessions
from gmemory.commands.save import save_memory
from gmemory.commands.mark import mark_session


def process_sessions(
    limit: int = 5,
    agent: str = "opencode",
    auto_mark: bool = False,
) -> Dict[str, Any]:
    """Fetch unprocessed sessions and return them for processing.

    This is the first step of the workflow loop:
    1. process_sessions() -> get sessions to review
    2. User/Agent reviews and distills content
    3. save_batch() or individual save_memory() calls

    Args:
        limit: Maximum number of sessions to fetch.
        agent: Agent type to fetch sessions for.
        auto_mark: If True, automatically mark sessions as processed
                   even if no memory is saved (for skipping sessions).

    Returns:
        Dict with:
        - sessions: List of session data
        - total: Number of sessions returned
        - hint: Usage hint for next steps
    """
    result = fetch_unprocessed_sessions(limit=limit, agent=agent)

    if "error" in result:
        return result

    sessions = result.get("sessions", [])

    return {
        "sessions": sessions,
        "total": len(sessions),
        "hint": (
            "Review sessions and call 'gmemory save --session-id=<id> --content=<distilled>' "
            "for each valuable session, or 'gmemory mark --session-id=<id>' to skip."
        ),
    }


def save_batch(
    memories: List[Dict[str, Any]],
    mark_sessions: bool = True,
) -> Dict[str, Any]:
    """Save multiple memories in a single batch operation.

    This is a convenience function for saving multiple distilled memories
    at once, typically after reviewing sessions from process_sessions().

    Args:
        memories: List of memory dicts, each containing:
            - session_id: (required) Source session ID
            - content: (required) Distilled memory content
            - tags: (optional) Comma-separated tags
            - importance: (optional) high/medium/low
            - type: (optional) Memory type
        mark_sessions: If True, mark sessions as processed after saving.

    Returns:
        Dict with:
        - saved: List of successfully saved memory IDs
        - failed: List of failed saves with error messages
        - marked: List of marked session IDs
    """
    saved = []
    failed = []
    marked = []

    for mem in memories:
        session_id = mem.get("session_id")
        content = mem.get("content")

        if not session_id:
            failed.append({"error": "Missing session_id", "input": mem})
            continue

        if not content:
            # No content = skip this session, just mark it
            if mark_sessions:
                try:
                    mark_session(session_id=session_id)
                    marked.append(session_id)
                except Exception as e:
                    failed.append(
                        {
                            "session_id": session_id,
                            "error": f"Failed to mark: {e}",
                        }
                    )
            continue

        try:
            result = save_memory(
                session_id=session_id,
                content=content,
                tags=mem.get("tags"),
                importance=mem.get("importance", "medium"),
                memory_type=mem.get("type"),
            )

            if "error" in result:
                failed.append(
                    {
                        "session_id": session_id,
                        "error": result["error"],
                    }
                )
            else:
                saved.append(result.get("memory_id", session_id))
                if mark_sessions:
                    marked.append(session_id)

        except Exception as e:
            failed.append(
                {
                    "session_id": session_id,
                    "error": str(e),
                }
            )

    return {
        "saved": saved,
        "failed": failed,
        "marked": marked,
        "summary": f"Saved {len(saved)}, failed {len(failed)}, marked {len(marked)}",
    }


def quick_save(
    session_id: str,
    content: str,
    tags: Optional[str] = None,
    importance: str = "medium",
    memory_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Quick save a single memory - convenience wrapper.

    Equivalent to: gmemory save --session-id=X --content=Y

    Args:
        session_id: Source session ID.
        content: Distilled memory content.
        tags: Optional comma-separated tags.
        importance: Importance level (high/medium/low).
        memory_type: Optional memory type.

    Returns:
        Result dict from save_memory.
    """
    return save_memory(
        session_id=session_id,
        content=content,
        tags=tags,
        importance=importance,
        memory_type=memory_type,
    )


def skip_session(session_id: str) -> Dict[str, Any]:
    """Mark a session as processed without saving a memory.

    Use this when a session has been reviewed but contains no
    valuable information worth persisting.

    Args:
        session_id: Session ID to mark as processed.

    Returns:
        Result dict from mark_session.
    """
    return mark_session(session_id=session_id)
