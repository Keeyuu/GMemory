"""Fetch command for GMemory."""

from typing import Dict, Any, Optional, List

from gmemory.config import config
from gmemory.scanner.base import ScannerRegistry
from gmemory.storage.database import MemoryDatabase

# Import to trigger registration
from gmemory.scanner import opencode, copilot  # noqa: F401


def _fetch_imported_unprocessed_sessions(
    limit: int,
    agent: Optional[str],
) -> List[Any]:
    if limit <= 0:
        return []

    db = MemoryDatabase()
    try:
        return db.get_unprocessed_imported_sessions(limit=limit, agent=agent)
    finally:
        db.close()


def fetch_unprocessed_sessions(
    limit: int = 10,
    agent: Optional[str] = None,
    scanner_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch unprocessed sessions from Agent logs.

    Args:
        limit: Maximum number of sessions to return.
        agent: Agent identifier to filter by. Defaults to config.default_agent.
        scanner_type: Scanner type to use (e.g., "opencode"). Defaults to config.default_agent.

    Returns:
        Dict containing:
        - sessions: List of session dictionaries
        - has_more: Boolean indicating if more sessions might be available
        - remaining: Number of remaining sessions (0 if unknown)
    """
    requested_scanner = scanner_type or config.default_scanner
    if agent and not scanner_type and agent != "all":
        requested_scanner = agent

    if requested_scanner == "all":
        imported_agent = agent if agent and agent != "all" else None
        sessions = _fetch_imported_unprocessed_sessions(
            limit=limit, agent=imported_agent
        )
        seen_ids = set()
        for imported in sessions:
            seen_ids.add(f"{imported.agent}:{imported.session_id}")

        available_scanners = sorted(ScannerRegistry.list_scanners())

        if not available_scanners:
            sessions_data = [session.to_dict() for session in sessions]
            return {
                "sessions": sessions_data,
                "has_more": len(sessions) >= limit,
                "remaining": 0,
            }

        if agent and agent != "all":
            if agent not in available_scanners:
                return {
                    "sessions": [],
                    "has_more": False,
                    "remaining": 0,
                    "error": f"Unknown scanner type: {agent}. Available: {available_scanners}",
                }
            target_scanners = [agent]
        else:
            target_scanners = available_scanners

        for scanner_name in target_scanners:
            if len(sessions) >= limit:
                break

            scanner = ScannerRegistry.create(
                name=scanner_name,
                agent=scanner_name,
                incremental=True,
            )
            if scanner is None:
                continue

            remaining_limit = max(1, limit - len(sessions))
            scanned_sessions = scanner.get_unprocessed_sessions(remaining_limit)
            for scanned in scanned_sessions:
                session_key = f"{scanned.agent}:{scanned.session_id}"
                if session_key in seen_ids:
                    continue
                seen_ids.add(session_key)
                sessions.append(scanned)
                if len(sessions) >= limit:
                    break
    else:
        effective_agent = agent or requested_scanner
        sessions = _fetch_imported_unprocessed_sessions(
            limit=limit,
            agent=effective_agent,
        )
        seen_ids = {f"{item.agent}:{item.session_id}" for item in sessions}

        scanner = ScannerRegistry.create(
            name=requested_scanner,
            agent=effective_agent,
            incremental=True,
        )

        if scanner is None:
            return {
                "sessions": [],
                "has_more": False,
                "remaining": 0,
                "error": f"Unknown scanner type: {requested_scanner}. Available: {ScannerRegistry.list_scanners()}",
            }

        remaining_limit = max(0, limit - len(sessions))
        if remaining_limit > 0:
            scanned_sessions = scanner.get_unprocessed_sessions(remaining_limit)
            for scanned in scanned_sessions:
                session_key = f"{scanned.agent}:{scanned.session_id}"
                if session_key in seen_ids:
                    continue
                seen_ids.add(session_key)
                sessions.append(scanned)
                if len(sessions) >= limit:
                    break

    # Convert Session objects to dictionaries for JSON serialization
    sessions_data = [session.to_dict() for session in sessions]

    # Heuristic: if we received the limit, there are likely more sessions.
    has_more = len(sessions) >= limit

    return {"sessions": sessions_data, "has_more": has_more, "remaining": 0}
