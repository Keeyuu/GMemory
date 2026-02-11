"""Workflow command for GMemory - single command automation loop."""

import json
import time
from typing import Any, Dict, List, Optional

from gmemory.commands.fetch import fetch_unprocessed_sessions
from gmemory.commands.save import save_memory
from gmemory.commands.mark import mark_session
from gmemory.errors import CommandError, ErrorCode
from gmemory.container import get_container


def process_sessions(
    limit: int = 5,
    agent: Optional[str] = None,
    scanner_type: Optional[str] = None,
    auto_mark: bool = False,
    show_backlog: bool = True,
) -> Dict[str, Any]:
    """Fetch unprocessed sessions and return them for processing.

    This is the first step of the workflow loop:
    1. process_sessions() -> get sessions to review
    2. User/Agent reviews and distills content
    3. save_batch() or individual save_memory() calls

    Args:
        limit: Maximum number of sessions to fetch.
        agent: Agent type to fetch sessions for.
        scanner_type: Scanner type to use (e.g. "opencode", "all").
        auto_mark: If True, automatically mark sessions as processed
                   even if no memory is saved (for skipping sessions).
        show_backlog: If True, include backlog statistics in response.

    Returns:
        Dict with:
        - sessions: List of session data
        - total: Number of sessions returned
        - backlog: Backlog statistics (if show_backlog=True)
        - workflow: Suggested workflow commands
        - hint: Usage hint for next steps
    """
    resolved_agent = agent or "all"
    result = fetch_unprocessed_sessions(
        limit=limit,
        agent=resolved_agent,
        scanner_type=scanner_type,
    )

    if "error" in result:
        return result

    sessions = result.get("sessions", [])
    has_more = result.get("has_more", False)

    response: Dict[str, Any] = {
        "sessions": sessions,
        "total": len(sessions),
    }

    # Add backlog statistics
    if show_backlog:
        backlog_info = _get_backlog_stats(
            resolved_agent,
            len(sessions),
            has_more,
            limit,
            scanner_type=scanner_type,
        )
        response["backlog"] = backlog_info

    # Generate workflow suggestions based on session count
    workflow = _generate_workflow_suggestions(sessions, resolved_agent)
    response["workflow"] = workflow

    # Contextual hint based on situation
    if len(sessions) == 0:
        response["hint"] = "No unprocessed sessions. Memory system is up to date."
        response["status"] = "up_to_date"
    elif len(sessions) == 1:
        session = sessions[0]
        session_id = session.get("session_id", "")
        response["hint"] = (
            f"1 session to review. Use:\n"
            f'  gmemory save --session-id={session_id} --content="<distilled>" --tags="<tags>"\n'
            f"  or: gmemory mark --session-id={session_id}  (to skip)"
        )
        response["status"] = "pending"
    else:
        response["hint"] = (
            f"{len(sessions)} sessions to review. Options:\n"
            f"  1. Process individually: gmemory save --session-id=<id> --content=<distilled>\n"
            f"  2. Batch process: Use save_batch() programmatically\n"
            f"  3. Skip all: gmemory mark-all --agent={resolved_agent} --limit={len(sessions)}"
        )
        response["status"] = "pending"
        if has_more:
            response["hint"] += (
                f"\n  Note: More sessions available beyond limit={limit}"
            )

    return response


def _get_backlog_stats(
    agent: str,
    fetched: int,
    has_more: bool,
    limit: int,
    scanner_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Get backlog statistics for workflow visibility.

    Args:
        agent: Agent type.
        fetched: Number of sessions fetched.
        has_more: Whether more sessions are available.
        limit: Fetch limit used.
        scanner_type: Scanner type used for fetching.

    Returns:
        Dict with backlog statistics.
    """
    container = get_container()

    stats: Dict[str, Any] = {
        "fetched": fetched,
        "has_more": has_more,
        "limit_used": limit,
    }

    try:
        db = container.get_database()
        # Get total processed sessions count
        if agent == "all":
            stats["total_processed"] = db.get_stats()["processed_sessions"]
        else:
            stats["total_processed"] = db.get_processed_session_count(agent)

        # Get scan error count
        stats["unresolved_errors"] = db.get_unresolved_error_count()

        # Estimate backlog size if has_more
        if has_more:
            # Fetch a larger sample to estimate
            larger_result = fetch_unprocessed_sessions(
                limit=100,
                agent=agent,
                scanner_type=scanner_type,
            )
            larger_sessions = larger_result.get("sessions", [])
            if len(larger_sessions) >= 100:
                stats["estimated_backlog"] = "100+"
                stats["backlog_warning"] = (
                    "Large backlog detected. Consider batch processing or "
                    "increasing limit with: gmemory process --limit=50"
                )
            else:
                stats["estimated_backlog"] = len(larger_sessions)
        else:
            stats["estimated_backlog"] = fetched

    except Exception:
        pass  # Non-critical, continue without stats

    return stats


def _generate_workflow_suggestions(
    sessions: List[Dict[str, Any]], agent: str
) -> Dict[str, Any]:
    """Generate contextual workflow command suggestions.

    Args:
        sessions: List of fetched sessions.
        agent: Agent type.

    Returns:
        Dict with suggested commands.
    """
    suggestions: Dict[str, Any] = {
        "commands": [],
    }

    if not sessions:
        suggestions["next_action"] = "none"
        suggestions["commands"] = [
            {
                "action": "search",
                "command": 'gmemory q "<query>"',
                "description": "Search existing memories",
            },
            {
                "action": "recent",
                "command": "gmemory recent",
                "description": "View recent memories",
            },
        ]
        return suggestions

    # Single session - provide specific commands
    if len(sessions) == 1:
        session = sessions[0]
        session_id = session.get("session_id", "")
        suggestions["next_action"] = "review_single"
        suggestions["commands"] = [
            {
                "action": "save",
                "command": f'gmemory save --session-id={session_id} --content="<distilled>" --tags="<tags>"',
                "description": "Save distilled memory from this session",
            },
            {
                "action": "skip",
                "command": f'gmemory mark --session-id={session_id} --status=skipped --reason="<reason>"',
                "description": "Mark as skipped with reason",
            },
            {
                "action": "detail",
                "command": f"gmemory session-detail {session_id}",
                "description": "View full session details",
            },
        ]
        return suggestions

    # Multiple sessions - provide batch options
    session_ids = [s.get("session_id", "") for s in sessions[:5]]
    suggestions["next_action"] = "review_batch"
    suggestions["session_ids"] = session_ids
    suggestions["commands"] = [
        {
            "action": "save_first",
            "command": f'gmemory save --session-id={session_ids[0]} --content="<distilled>" --tags="<tags>"',
            "description": "Save first session",
        },
        {
            "action": "mark_all",
            "command": f'gmemory mark-all --agent={agent} --limit={len(sessions)} --reason="<reason>"',
            "description": "Mark all as processed (skip) with reason",
        },
        {
            "action": "export_review",
            "command": f"gmemory session-export {session_ids[0]}",
            "description": "Export session for offline review",
        },
    ]

    return suggestions


def save_batch(
    memories: List[Dict[str, Any]],
    mark_sessions: bool = True,
    skip_reason: Optional[str] = None,
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
            - skip_reason: (optional) reason for skipping when content is empty
        mark_sessions: If True, mark sessions as processed after saving.
        skip_reason: Required reason when marking sessions without content.

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
                    reason = mem.get("skip_reason") or skip_reason
                    if not reason:
                        raise CommandError(
                            code=ErrorCode.CMD_MISSING_REQUIRED,
                            message="Missing skip_reason for empty content",
                            details={"session_id": session_id},
                        )
                    mark_session(
                        session_id=session_id,
                        status="skipped",
                        reason=reason,
                    )
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
                skip_reason=mem.get("skip_reason") or skip_reason,
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
    return mark_session(session_id=session_id, status="skipped", reason="manual skip")


def mark_all_sessions(
    agent: str = "all",
    limit: int = 10,
    dry_run: bool = True,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Mark multiple unprocessed sessions as processed (batch skip).

    Use this to quickly clear a backlog of sessions that don't need
    memory extraction.

    Args:
        agent: Agent type to mark sessions for.
        limit: Maximum number of sessions to mark.
        dry_run: If True, preview what would be marked without applying.
        reason: Required reason when applying batch skip.

    Returns:
        Dict with:
        - marked: List of marked session IDs (or would-be marked if dry_run)
        - failed: List of failed marks with errors
        - dry_run: Whether this was a dry run
        - summary: Human-readable summary
    """
    # Fetch unprocessed sessions
    result = fetch_unprocessed_sessions(limit=limit, agent=agent)

    if "error" in result:
        return result

    sessions = result.get("sessions", [])

    if not sessions:
        return {
            "marked": [],
            "failed": [],
            "dry_run": dry_run,
            "summary": "No unprocessed sessions to mark.",
        }

    session_ids = [s.get("session_id", "") for s in sessions if s.get("session_id")]

    if dry_run:
        return {
            "marked": session_ids,
            "failed": [],
            "dry_run": True,
            "summary": f"Would mark {len(session_ids)} session(s) as processed.",
            "hint": "Use --apply to actually mark these sessions.",
        }

    if not reason:
        raise CommandError(
            code=ErrorCode.CMD_MISSING_REQUIRED,
            message="Missing reason for batch mark",
            details={"required": "reason"},
        )

    # Actually mark sessions
    marked = []
    failed = []

    for session_id in session_ids:
        try:
            mark_session(session_id=session_id, status="skipped", reason=reason)
            marked.append(session_id)
        except Exception as e:
            failed.append({"session_id": session_id, "error": str(e)})

    return {
        "marked": marked,
        "failed": failed,
        "dry_run": False,
        "summary": f"Marked {len(marked)} session(s), {len(failed)} failed.",
    }


def get_scan_error_summary() -> Dict[str, Any]:
    """Get a summary of scan errors with suggested actions.

    Provides visibility into scan errors and actionable recommendations
    for resolving them.

    Returns:
        Dict with:
        - total_errors: Total unresolved errors
        - by_error_code: Breakdown by error code
        - by_file: Breakdown by file path
        - recent_errors: Most recent errors with details
        - suggestions: Recommended actions
    """
    container = get_container()
    db = container.get_database()

    # Get all unresolved errors
    errors = db.get_scan_errors(limit=100, unresolved_only=True)

    if not errors:
        return {
            "total_errors": 0,
            "status": "healthy",
            "message": "No unresolved scan errors.",
        }

    # Group by error code
    by_code: Dict[str, List[Dict[str, Any]]] = {}
    for err in errors:
        code = err.get("error_code") or "UNKNOWN"
        if code not in by_code:
            by_code[code] = []
        by_code[code].append(err)

    # Group by file path
    by_file: Dict[str, int] = {}
    for err in errors:
        file_path = err.get("file_path") or "unknown"
        # Truncate long paths
        if len(file_path) > 50:
            file_path = "..." + file_path[-47:]
        by_file[file_path] = by_file.get(file_path, 0) + 1

    # Generate suggestions based on error patterns
    suggestions = _generate_error_suggestions(by_code, errors)

    # Get recent errors with details
    recent = errors[:5]
    recent_formatted = [
        {
            "id": e.get("id"),
            "error_code": e.get("error_code"),
            "message": (e.get("error_message", "")[:100] + "...")
            if len(e.get("error_message", "")) > 100
            else e.get("error_message", ""),
            "file": e.get("file_path", "")[-50:] if e.get("file_path") else None,
            "session_id": e.get("session_id"),
        }
        for e in recent
    ]

    return {
        "total_errors": len(errors),
        "status": "needs_attention" if len(errors) > 10 else "minor_issues",
        "by_error_code": {code: len(errs) for code, errs in by_code.items()},
        "by_file": dict(sorted(by_file.items(), key=lambda x: x[1], reverse=True)[:10]),
        "recent_errors": recent_formatted,
        "suggestions": suggestions,
    }


def unmark_sessions(
    session_ids: List[str],
    agent: str = "opencode",
) -> Dict[str, Any]:
    """Remove processed markers so sessions can be re-processed.

    Args:
        session_ids: Session IDs to unmark.
        agent: Agent identifier.

    Returns:
        Dict with deleted count and missing IDs.
    """
    container = get_container()
    db = container.get_database()

    deleted = db.delete_processed_sessions(agent=agent, session_ids=session_ids)
    return {
        "deleted": deleted,
        "requested": len(session_ids),
    }


def _generate_error_suggestions(
    by_code: Dict[str, List[Dict[str, Any]]], all_errors: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """Generate actionable suggestions based on error patterns.

    Args:
        by_code: Errors grouped by error code.
        all_errors: All error records.

    Returns:
        List of suggestion dicts with action and command.
    """
    suggestions = []

    # Check for common error patterns
    if "GMEM-SCAN-101" in by_code or "JSON" in str(by_code).upper():
        suggestions.append(
            {
                "issue": "JSON parsing errors",
                "action": "Some session files may be corrupted or incomplete",
                "command": "gmemory scan-errors --limit=10  # Review specific files",
            }
        )

    if "GMEM-SCAN-102" in by_code or "PERMISSION" in str(by_code).upper():
        suggestions.append(
            {
                "issue": "Permission errors",
                "action": "Check file permissions on session log directory",
                "command": "ls -la ~/.local/share/opencode/storage/",
            }
        )

    if len(all_errors) > 20:
        suggestions.append(
            {
                "issue": "Large number of errors",
                "action": "Consider bulk resolution after review",
                "command": f"gmemory scan-errors-resolve {' '.join(str(e['id']) for e in all_errors[:10])} --note='Bulk resolved'",
            }
        )

    # Always suggest review command
    if all_errors:
        error_ids = [str(e.get("id")) for e in all_errors[:5] if e.get("id")]
        suggestions.append(
            {
                "issue": "Unresolved errors need attention",
                "action": "Review and resolve errors to prevent re-processing attempts",
                "command": f"gmemory scan-errors-resolve {' '.join(error_ids)} --note='Reviewed and resolved'",
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "issue": "Minor errors detected",
                "action": "Review errors and resolve as needed",
                "command": "gmemory scan-errors",
            }
        )

    return suggestions


def batch_resolve_errors(
    error_ids: Optional[List[int]] = None,
    resolve_all: bool = False,
    note: Optional[str] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Batch resolve scan errors.

    Args:
        error_ids: Specific error IDs to resolve. If None and resolve_all=True,
                   resolves all unresolved errors.
        resolve_all: If True and error_ids is None, resolve all errors.
        note: Resolution note to attach.
        dry_run: If True, preview what would be resolved.

    Returns:
        Dict with resolution results.
    """
    container = get_container()
    db = container.get_database()

    if error_ids:
        ids_to_resolve = error_ids
    elif resolve_all:
        errors = db.get_scan_errors(limit=1000, unresolved_only=True)
        ids_to_resolve = [e["id"] for e in errors if e.get("id")]
    else:
        return {
            "error": "Must specify error_ids or use resolve_all=True",
        }

    if not ids_to_resolve:
        return {
            "resolved": [],
            "failed": [],
            "dry_run": dry_run,
            "summary": "No errors to resolve.",
        }

    if dry_run:
        return {
            "would_resolve": ids_to_resolve,
            "count": len(ids_to_resolve),
            "dry_run": True,
            "summary": f"Would resolve {len(ids_to_resolve)} error(s).",
            "hint": "Use --apply to actually resolve these errors.",
        }

    result = db.resolve_scan_errors(ids_to_resolve, note=note)
    return {
        "resolved": result.get("resolved", []),
        "failed": result.get("failed", []),
        "dry_run": False,
        "summary": f"Resolved {len(result.get('resolved', []))} error(s), {len(result.get('failed', []))} failed.",
    }
