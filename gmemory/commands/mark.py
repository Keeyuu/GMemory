import time
from typing import Dict, Any, Optional

from gmemory.config import config
from gmemory.models import ProcessedSession
from gmemory.storage.database import MemoryDatabase


def mark_session(
    session_id: str,
    agent: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mark a session as processed without saving a specific memory.

    Args:
        session_id: The ID of the session to mark.
        agent: The agent identifier. Defaults to config.default_agent.

    Returns:
        Dict containing:
        - session_id: The ID of the session.
        - marked: Boolean indicating success.
    """
    # Resolve agent
    if not agent:
        agent = config.default_agent

    current_time = int(time.time())
    db = None

    try:
        db = MemoryDatabase()

        # Create ProcessedSession object
        processed_session = ProcessedSession(
            agent=agent,
            session_id=session_id,
            processed_at=current_time,
        )

        # Add to database
        db.add_processed_session(processed_session)

        return {
            "session_id": session_id,
            "marked": True,
        }

    except Exception as e:
        # Re-raise exception to be handled by caller
        raise e
    finally:
        if db:
            db.close()
