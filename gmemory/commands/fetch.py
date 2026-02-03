from typing import Dict, Any, Optional, List
from gmemory.config import config
from gmemory.scanner.opencode import OpenCodeScanner


def fetch_unprocessed_sessions(
    limit: int = 10, agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch unprocessed sessions from Agent logs.

    Args:
        limit: Maximum number of sessions to return.
        agent: Agent identifier to filter by. Defaults to config.default_agent.

    Returns:
        Dict containing:
        - sessions: List of session dictionaries
        - has_more: Boolean indicating if more sessions might be available
        - remaining: Number of remaining sessions (0 if unknown)
    """
    # Respect agent argument for filtering (pass via config.default_agent if none)
    # Since OpenCodeScanner uses config.default_agent, we override it if agent is provided.
    original_agent = config.default_agent

    # We explicitly handle the agent override here because OpenCodeScanner relies on
    # config.default_agent internally and doesn't accept an agent argument.
    if agent:
        # Accessing _config directly as we cannot modify other files to add setters
        # or change Scanner signature.
        if "scanner" not in config._config:
            config._config["scanner"] = {}
        config._config["scanner"]["default_agent"] = agent

    try:
        scanner = OpenCodeScanner()
        sessions = scanner.get_unprocessed_sessions(limit)

        # Convert Session objects to dictionaries for JSON serialization
        sessions_data = [session.to_dict() for session in sessions]

        # Heuristic: if we received the limit, there are likely more sessions.
        # Precise 'remaining' count is not available from current scanner API.
        has_more = len(sessions) >= limit

        return {"sessions": sessions_data, "has_more": has_more, "remaining": 0}
    finally:
        # Restore configuration to avoid side effects
        if agent:
            config._config["scanner"]["default_agent"] = original_agent
