"""Database schema migrations for GMemory.

Provides a minimal migration system to track and apply schema changes.
Each migration is a function that takes a connection and applies changes.

Migration naming: NNNN_description where NNNN is a zero-padded version number.
"""

import logging
import sqlite3
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Type alias for migration functions
MigrationFunc = Callable[[sqlite3.Connection], None]

# Registry of all migrations: version -> (description, migration_func)
MIGRATIONS: Dict[int, Tuple[str, MigrationFunc]] = {}


def migration(version: int, description: str):
    """Decorator to register a migration function.

    Args:
        version: Schema version number (must be unique and sequential).
        description: Human-readable description of the migration.
    """

    def decorator(func: MigrationFunc) -> MigrationFunc:
        if version in MIGRATIONS:
            raise ValueError(f"Duplicate migration version: {version}")
        MIGRATIONS[version] = (description, func)
        return func

    return decorator


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version from the database.

    Returns 0 if no version table exists (fresh database).
    """
    try:
        cursor = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return 0


def init_version_table(conn: sqlite3.Connection) -> None:
    """Create the schema version tracking table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
        )
    """)


def apply_migrations(conn: sqlite3.Connection) -> List[int]:
    """Apply all pending migrations.

    Args:
        conn: SQLite connection.

    Returns:
        List of applied migration versions.
    """
    init_version_table(conn)
    current_version = get_current_version(conn)
    applied = []

    # Get migrations to apply (sorted by version)
    pending = sorted(
        [
            (v, desc, func)
            for v, (desc, func) in MIGRATIONS.items()
            if v > current_version
        ]
    )

    for version, description, migrate_func in pending:
        logger.info(f"Applying migration {version}: {description}")
        try:
            with conn:
                migrate_func(conn)
                conn.execute(
                    "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                    (version, description),
                )
            applied.append(version)
            logger.info(f"Migration {version} applied successfully")
        except Exception as e:
            logger.error(f"Migration {version} failed: {e}")
            raise

    return applied


def get_migration_status(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Get migration status information.

    Returns:
        Dict with current_version, latest_available, pending_count, and history.
    """
    init_version_table(conn)
    current = get_current_version(conn)
    latest = max(MIGRATIONS.keys()) if MIGRATIONS else 0
    pending = [v for v in MIGRATIONS.keys() if v > current]

    # Get applied migrations history
    history = []
    try:
        cursor = conn.execute(
            "SELECT version, description, applied_at FROM schema_version ORDER BY version"
        )
        history = [
            {"version": row[0], "description": row[1], "applied_at": row[2]}
            for row in cursor
        ]
    except sqlite3.OperationalError:
        pass

    return {
        "current_version": current,
        "latest_available": latest,
        "pending_count": len(pending),
        "pending_versions": sorted(pending),
        "history": history,
    }


# =============================================================================
# Migration Definitions
# =============================================================================


@migration(1, "Initial schema - baseline for existing databases")
def migrate_v1(conn: sqlite3.Connection) -> None:
    """Baseline migration for existing databases.

    This migration doesn't change anything - it just marks existing
    databases as being at version 1 (the original schema).
    """
    # Check if memories table exists (existing database)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
    )
    if cursor.fetchone():
        logger.info("Existing database detected, marking as v1 baseline")
    # No schema changes needed - this is just a baseline marker


@migration(2, "Add superseded_by column for memory merging")
def migrate_v2(conn: sqlite3.Connection) -> None:
    """Add superseded_by column to support memory merging/replacement.

    When a memory is superseded by another, this column stores the ID
    of the newer memory. Superseded memories are excluded from search
    results by default but retained for history.
    """
    # Check if column already exists
    cursor = conn.execute("PRAGMA table_info(memories)")
    columns = [row[1] for row in cursor.fetchall()]

    if "superseded_by" not in columns:
        conn.execute("ALTER TABLE memories ADD COLUMN superseded_by TEXT DEFAULT NULL")
        logger.info("Added superseded_by column to memories table")

    # Create index for efficient filtering
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_superseded ON memories(superseded_by)"
    )


@migration(3, "Add scan run and error tracking tables")
def migrate_v3(conn: sqlite3.Connection) -> None:
    """Add tables for scan observability and recovery.

    Adds scan_runs for high-level scan metadata, and scan_errors
    for per-file error tracking with manual replay support.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_runs (
            id TEXT PRIMARY KEY,
            scanner TEXT NOT NULL,
            agent TEXT NOT NULL,
            base_dir TEXT,
            incremental INTEGER NOT NULL,
            limit_value INTEGER NOT NULL,
            started_at INTEGER NOT NULL,
            finished_at INTEGER,
            status TEXT NOT NULL,
            total_files INTEGER NOT NULL DEFAULT 0,
            scanned_files INTEGER NOT NULL DEFAULT 0,
            skipped_unchanged INTEGER NOT NULL DEFAULT 0,
            unprocessed_sessions INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            limit_reached INTEGER NOT NULL DEFAULT 0,
            note TEXT
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            file_path TEXT,
            session_id TEXT,
            error_code TEXT,
            error_message TEXT,
            occurred_at INTEGER NOT NULL,
            resolved INTEGER NOT NULL DEFAULT 0,
            resolved_at INTEGER,
            resolution_note TEXT
        )
    """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scan_runs_started_at ON scan_runs(started_at)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_runs_status ON scan_runs(status)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scan_errors_run_id ON scan_errors(run_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scan_errors_resolved ON scan_errors(resolved)"
    )
