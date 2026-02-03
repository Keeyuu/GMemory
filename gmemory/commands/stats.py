from typing import Dict, Any
from gmemory.storage.database import MemoryDatabase
from gmemory.scanner.opencode import OpenCodeScanner


def get_stats() -> Dict[str, Any]:
    """
    Get system statistics including memory count and session status.

    Returns:
        Dict containing:
        - total_memories: Total number of memories in DB.
        - processed_sessions: Number of sessions marked as processed.
        - unprocessed_sessions: Number of sessions found in OpenCode but not yet processed.
        - by_project: Dictionary mapping project names to memory counts.
        - by_importance: Dictionary mapping importance levels to memory counts.
    """
    db = None
    try:
        db = MemoryDatabase()
        db_stats = db.get_stats()

        # Count unprocessed sessions
        scanner = OpenCodeScanner()
        # Call get_unprocessed_sessions with high limit to get an approximate count
        unprocessed = scanner.get_unprocessed_sessions(limit=1000)
        unprocessed_count = len(unprocessed)

        # Breakdown by project
        by_project = {}
        cursor = db.conn.execute(
            "SELECT project_name, COUNT(*) as count FROM memories GROUP BY project_name"
        )
        for row in cursor:
            name = row["project_name"] or "Unknown"
            by_project[name] = row["count"]

        # Breakdown by importance
        by_importance = {}
        cursor = db.conn.execute(
            "SELECT importance, COUNT(*) as count FROM memories GROUP BY importance"
        )
        for row in cursor:
            imp = row["importance"] or "Unknown"
            by_importance[imp] = row["count"]

        return {
            "total_memories": db_stats["memories"],
            "processed_sessions": db_stats["processed_sessions"],
            "unprocessed_sessions": unprocessed_count,
            "by_project": by_project,
            "by_importance": by_importance,
        }
    finally:
        if db:
            db.close()
