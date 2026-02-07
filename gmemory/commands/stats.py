"""Stats command for GMemory."""

from typing import Dict, Any

from gmemory.config import config
from gmemory.storage.database import MemoryDatabase
from gmemory.scanner.base import ScannerRegistry

# Import to trigger registration
from gmemory.scanner import opencode, copilot  # noqa: F401


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

        total_sessions = 0
        unprocessed_count = 0
        requested_scanner = config.default_scanner

        if requested_scanner == "all":
            for scanner_name in sorted(ScannerRegistry.list_scanners()):
                scanner = ScannerRegistry.create(
                    name=scanner_name,
                    incremental=False,
                )
                if not scanner:
                    continue
                scanner_total = scanner.count_sessions()
                scanner_processed = db.get_processed_session_count(scanner_name)
                total_sessions += scanner_total
                unprocessed_count += max(0, scanner_total - scanner_processed)
        else:
            scanner_name = requested_scanner
            scanner = ScannerRegistry.create(
                name=scanner_name,
                incremental=False,
            )
            if scanner:
                total_sessions = scanner.count_sessions()
                scanner_processed = db.get_processed_session_count(scanner_name)
                unprocessed_count = max(0, total_sessions - scanner_processed)

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

        top_hot = db.get_hot_memories(limit=5)
        top_cold = db.get_cold_memories(limit=5, min_age_days=7)

        return {
            "total_memories": db_stats["memories"],
            "processed_sessions": db_stats["processed_sessions"],
            "unprocessed_sessions": unprocessed_count,
            "scan_runs": db_stats["scan_runs"],
            "scan_errors": db_stats["scan_errors"],
            "by_project": by_project,
            "by_importance": by_importance,
            "top_hot": top_hot,
            "top_cold": top_cold,
        }
    finally:
        if db:
            db.close()
