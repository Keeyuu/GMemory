"""Fetch command for GMemory."""

from typing import Dict, Any, Optional, List

from gmemory.config import config
from gmemory.scanner.base import ScannerRegistry

# Import to trigger registration
from gmemory.scanner import opencode, copilot  # noqa: F401


def fetch_unprocessed_sessions(
    limit: int = 10,
    agent: Optional[str] = None,
    scanner_type: Optional[str] = None,
    offset: int = 0,
    cursor: Optional[str] = None,
    compact: bool = False,
) -> Dict[str, Any]:
    """
    Fetch unprocessed sessions from Agent logs.

    Args:
        limit: Maximum number of sessions to return.
        agent: Agent identifier to filter by. Defaults to config.default_agent.
        scanner_type: Scanner type to use (e.g., "opencode"). Defaults to config.default_agent.
        offset: Pagination offset.
        cursor: Pagination cursor. If provided, takes precedence over offset.
        compact: Return compact session metadata only when True.

    Returns:
        Dict containing:
        - sessions: List of session dictionaries
        - has_more: Boolean indicating if more sessions might be available
        - remaining: Number of total pending sessions (backward compatible)
        - total_pending: Total pending sessions
        - returned: Count of returned sessions in this page
        - remaining_after_page: Remaining sessions after this page
        - offset: Actual offset used for this page
        - next_cursor: Next cursor string when has_more=True, otherwise None
    """

    def _error_response(message: str) -> Dict[str, Any]:
        return {
            "sessions": [],
            "has_more": False,
            "remaining": 0,
            "total_pending": 0,
            "returned": 0,
            "remaining_after_page": 0,
            "offset": 0,
            "next_cursor": None,
            "error": message,
        }

    def _parse_non_negative_int(value: Any, field_name: str) -> int:
        if isinstance(value, bool):
            raise ValueError(f"{field_name} must be a non-negative integer")
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_name} must be a non-negative integer") from None
        if parsed < 0:
            raise ValueError(f"{field_name} must be a non-negative integer")
        return parsed

    try:
        effective_offset = (
            _parse_non_negative_int(cursor, "cursor")
            if cursor is not None
            else _parse_non_negative_int(offset, "offset")
        )
    except ValueError as exc:
        return _error_response(str(exc))

    requested_scanner = scanner_type or config.default_scanner
    if agent and not scanner_type and agent != "all":
        requested_scanner = agent

    if limit <= 0:
        return {
            "sessions": [],
            "has_more": False,
            "remaining": 0,
            "total_pending": 0,
            "returned": 0,
            "remaining_after_page": 0,
            "offset": effective_offset,
            "next_cursor": None,
        }

    if requested_scanner == "all":
        available_scanners = sorted(ScannerRegistry.list_scanners())
        if not available_scanners:
            return {
                "sessions": [],
                "has_more": False,
                "remaining": 0,
                "total_pending": 0,
                "returned": 0,
                "remaining_after_page": 0,
                "offset": effective_offset,
                "next_cursor": None,
            }

        if agent and agent != "all":
            if agent not in available_scanners:
                return {
                    "sessions": [],
                    "has_more": False,
                    "remaining": 0,
                    "total_pending": 0,
                    "returned": 0,
                    "remaining_after_page": 0,
                    "offset": effective_offset,
                    "next_cursor": None,
                    "error": f"Unknown scanner type: {agent}. Available: {available_scanners}",
                }
            target_scanners = [agent]
        else:
            target_scanners = available_scanners
    else:
        target_scanners = [requested_scanner]

    scanner_entries: List[tuple[Any, int]] = []
    total_pending = 0
    for scanner_name in target_scanners:
        scanner_agent = (
            agent
            if (agent and agent != "all" and requested_scanner != "all")
            else scanner_name
        )
        scanner = ScannerRegistry.create(
            name=scanner_name,
            agent=scanner_agent,
            incremental=True,
        )
        if scanner is None:
            if requested_scanner != "all":
                return {
                    "sessions": [],
                    "has_more": False,
                    "remaining": 0,
                    "total_pending": 0,
                    "returned": 0,
                    "remaining_after_page": 0,
                    "offset": effective_offset,
                    "next_cursor": None,
                    "error": f"Unknown scanner type: {requested_scanner}. Available: {ScannerRegistry.list_scanners()}",
                }
            continue

        scanner_total = max(scanner.count_unprocessed(), 0)
        total_pending += scanner_total
        scanner_entries.append((scanner, scanner_total))

    if total_pending <= 0:
        return {
            "sessions": [],
            "has_more": False,
            "remaining": 0,
            "total_pending": 0,
            "returned": 0,
            "remaining_after_page": 0,
            "offset": effective_offset,
            "next_cursor": None,
        }

    if effective_offset >= total_pending:
        return {
            "sessions": [],
            "has_more": False,
            "remaining": total_pending,
            "total_pending": total_pending,
            "returned": 0,
            "remaining_after_page": 0,
            "offset": effective_offset,
            "next_cursor": None,
        }

    page_start = effective_offset
    page_end = effective_offset + limit
    page_sessions: List[Any] = []
    seen_ids = set()
    aggregate_cursor = 0

    for scanner, scanner_total in scanner_entries:
        if scanner_total <= 0:
            continue

        scanner_start = aggregate_cursor
        scanner_end = aggregate_cursor + scanner_total

        if scanner_end <= page_start:
            aggregate_cursor = scanner_end
            continue

        if scanner_start >= page_end:
            break

        local_start = max(0, page_start - scanner_start)
        local_end = min(scanner_total, page_end - scanner_start)
        fetch_count = max(local_end, 0)

        if fetch_count <= 0:
            aggregate_cursor = scanner_end
            continue

        scanned_sessions = scanner.get_unprocessed_sessions(fetch_count)
        if local_start >= len(scanned_sessions):
            aggregate_cursor = scanner_end
            continue

        for scanned in scanned_sessions[local_start:local_end]:
            session_key = f"{scanned.agent}:{scanned.session_id}"
            if session_key in seen_ids:
                continue
            seen_ids.add(session_key)
            page_sessions.append(scanned)
            if len(page_sessions) >= limit:
                break

        aggregate_cursor = scanner_end
        if len(page_sessions) >= limit:
            break

    returned = len(page_sessions)
    has_more = (effective_offset + returned) < total_pending
    remaining_after_page = max(total_pending - (effective_offset + returned), 0)
    next_cursor = str(effective_offset + returned) if has_more else None

    if compact:
        sessions_data = [
            {
                "session_id": session.session_id,
                "agent": session.agent,
                "project_path": session.project_path,
                "project_name": session.project_name,
                "started_at": session.started_at,
                "message_count": len(session.messages),
            }
            for session in page_sessions
        ]
    else:
        sessions_data = [session.to_dict() for session in page_sessions]

    return {
        "sessions": sessions_data,
        "has_more": has_more,
        "remaining": total_pending,
        "total_pending": total_pending,
        "returned": returned,
        "remaining_after_page": remaining_after_page,
        "offset": effective_offset,
        "next_cursor": next_cursor,
    }
