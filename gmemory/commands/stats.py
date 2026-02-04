"""Stats command for GMemory."""

from typing import Dict, Any

from gmemory.config import config
from gmemory.storage.database import MemoryDatabase
from gmemory.scanner.base import ScannerRegistry

# Import to trigger registration
from gmemory.scanner import opencode  # noqa: F401


def get_stats() -> Dict[str, Any]:
    """
    Get system statistics including memory count and session status.

    Returns:
        Dict containing:
        - total_memories: Total number of memories in DB.
        - processed_sessions: Number of sessions marked as processed.
        - unprocessed_sessions: Estimated number of unprocessed sessions.
        - scan_runs: Total scan run records.
        - scan_errors: Unresolved scan errors.
        - by_project: Dictionary mapping project names to memory counts.
        - by_importance: Dictionary mapping importance levels to memory counts.
    """
    db = None
    try:
        db = MemoryDatabase()
        db_stats = db.get_stats()

        # Count sessions using lightweight method (no message loading)
        scanner = ScannerRegistry.create(
            name=config.default_agent,
            incremental=False,  # Don't need state tracking for stats
        )

        total_sessions = 0
        if scanner:
            total_sessions = scanner.count_sessions()

        # Unprocessed = total - processed
        unprocessed_count = max(0, total_sessions - db_stats["processed_sessions"])

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
            "scan_runs": db_stats["scan_runs"],
            "scan_errors": db_stats["scan_errors"],
            "by_project": by_project,
            "by_importance": by_importance,
        }
    finally:
        if db:
            db.close()
