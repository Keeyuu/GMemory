"""Fetch command for GMemory."""

from typing import Dict, Any, Optional

from gmemory.config import config
from gmemory.scanner.base import ScannerRegistry

# Import to trigger registration
from gmemory.scanner import opencode  # noqa: F401


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
    # Determine scanner type
    scanner_name = scanner_type or config.default_agent

    # Create scanner via registry
    scanner = ScannerRegistry.create(
        name=scanner_name,
        agent=agent or config.default_agent,
        incremental=True,
    )

    if scanner is None:
        return {
            "sessions": [],
            "has_more": False,
            "remaining": 0,
            "error": f"Unknown scanner type: {scanner_name}. Available: {ScannerRegistry.list_scanners()}",
        }

    sessions = scanner.get_unprocessed_sessions(limit)

    # Convert Session objects to dictionaries for JSON serialization
    sessions_data = [session.to_dict() for session in sessions]

    # Heuristic: if we received the limit, there are likely more sessions.
    has_more = len(sessions) >= limit

    return {"sessions": sessions_data, "has_more": has_more, "remaining": 0}
