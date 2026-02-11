"""Stats command for GMemory."""

from typing import Dict, Any

from gmemory.config import config
from gmemory.commands.native_cleanup import get_native_session_snapshot
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
        ghost_count = 0
        requested_scanner = config.default_scanner
        processed_total = db_stats["processed_sessions"]
        reprocess_count = db.conn.execute(
            """
            SELECT COUNT(*)
            FROM processed_sessions
            WHERE LOWER(COALESCE(reason, '')) LIKE '%reprocess%'
            """
        ).fetchone()[0]
        hash_mismatch_count = db.conn.execute(
            """
            SELECT COUNT(*)
            FROM processed_sessions
            WHERE LOWER(COALESCE(reason, '')) LIKE '%hash_mismatch%'
               OR LOWER(COALESCE(reason, '')) LIKE '%hash mismatch%'
            """
        ).fetchone()[0]

        processed_ids_global = {
            str(row["session_id"] or "")
            for row in db.conn.execute(
                "SELECT DISTINCT session_id FROM processed_sessions"
            )
            if str(row["session_id"] or "")
        }

        reprocess_rate = (
            round(reprocess_count / processed_total, 4) if processed_total > 0 else 0.0
        )
        hash_mismatch_rate = (
            round(hash_mismatch_count / processed_total, 4)
            if processed_total > 0
            else 0.0
        )

        if requested_scanner == "all":
            for scanner_name in sorted(ScannerRegistry.list_scanners()):
                snapshot = get_native_session_snapshot(scanner_name)
                if snapshot.get("supported"):
                    native_ids = snapshot.get("session_ids", set())
                    total_sessions += len(native_ids)
                    processed_ids = {
                        str(row["session_id"] or "")
                        for row in db.conn.execute(
                            "SELECT session_id FROM processed_sessions WHERE agent = ?",
                            (scanner_name,),
                        )
                        if str(row["session_id"] or "")
                    }
                    processed_existing = sum(
                        1
                        for session_id in native_ids
                        if session_id in processed_ids_global
                    )
                    ghost_count += sum(
                        1
                        for session_id in processed_ids
                        if session_id and session_id not in native_ids
                    )
                    unprocessed_count += max(0, len(native_ids) - processed_existing)
                else:
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
            snapshot = get_native_session_snapshot(scanner_name)
            if snapshot.get("supported"):
                native_ids = snapshot.get("session_ids", set())
                total_sessions = len(native_ids)
                processed_ids = {
                    str(row["session_id"] or "")
                    for row in db.conn.execute(
                        "SELECT session_id FROM processed_sessions WHERE agent = ?",
                        (scanner_name,),
                    )
                    if str(row["session_id"] or "")
                }
                processed_existing = sum(
                    1 for session_id in native_ids if session_id in processed_ids_global
                )
                ghost_count += sum(
                    1
                    for session_id in processed_ids
                    if session_id and session_id not in native_ids
                )
                unprocessed_count = max(0, len(native_ids) - processed_existing)
            else:
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
            "reprocess_rate": reprocess_rate,
            "hash_mismatch_rate": hash_mismatch_rate,
            "ghost_count": ghost_count,
            "cleanup_deleted_rows": 0,
            "by_project": by_project,
            "by_importance": by_importance,
            "top_hot": top_hot,
            "top_cold": top_cold,
        }
    finally:
        if db:
            db.close()
