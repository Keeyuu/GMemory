"""Quick access commands for GMemory.

Provides shortcut commands for common high-frequency operations
to reduce typing and improve CLI ergonomics.
"""

import time
from typing import Any, Dict, List, Optional

from gmemory.commands.search import search_memories
from gmemory.commands.session_report import get_session_report
from gmemory.storage.database import MemoryDatabase


def quick_search(
    query: str,
    limit: int = 5,
    recent_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Quick search with sensible defaults for fast lookups.

    Optimized for speed and minimal output. Uses compact mode
    and applies recency boost if recent_days is specified.

    Args:
        query: Search query.
        limit: Maximum results (default 5 for quick lookup).
        recent_days: If set, boost memories from last N days.

    Returns:
        Dict with compact search results.
    """
    recency_weight = 0.0
    if recent_days:
        # Scale recency weight based on days
        # 7 days -> 0.5, 30 days -> 0.3, 90 days -> 0.2
        if recent_days <= 7:
            recency_weight = 0.5
        elif recent_days <= 30:
            recency_weight = 0.3
        else:
            recency_weight = 0.2

    return search_memories(
        query=query,
        limit=limit,
        compact=True,
        recency_weight=recency_weight,
        mode="hybrid",
    )


def recent_memories(
    days: int = 7,
    limit: int = 10,
    project_path: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get most recent memories.

    Args:
        days: Look back N days (default 7).
        limit: Maximum results.
        project_path: Optional project filter.
        tags: Optional tag filter.

    Returns:
        Dict with recent memories.
    """
    db = MemoryDatabase()
    try:
        cutoff = time.time() - (days * 24 * 3600)

        # Build query
        query = """
            SELECT id, content, tags, importance, project_path, 
                   created_at, updated_at
            FROM memories 
            WHERE updated_at >= ?
            AND (superseded_by IS NULL OR superseded_by = '')
        """
        params: List[Any] = [cutoff]

        if project_path:
            query += " AND project_path = ?"
            params.append(project_path)

        if tags:
            # Filter by tags (memory must have all specified tags)
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f"%{tag}%")

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        cursor = db.conn.execute(query, params)
        rows = cursor.fetchall()

        memories = []
        for row in rows:
            memories.append(
                {
                    "id": row["id"],
                    "preview": row["content"][:150] + "..."
                    if len(row["content"]) > 150
                    else row["content"],
                    "tags": row["tags"].split(",") if row["tags"] else [],
                    "importance": row["importance"],
                    "project_path": row["project_path"],
                    "updated_at": row["updated_at"],
                    "age_hours": round((time.time() - row["updated_at"]) / 3600, 1),
                }
            )

        return {
            "memories": memories,
            "total": len(memories),
            "days": days,
            "cutoff_timestamp": cutoff,
        }

    finally:
        db.close()


def recent_sessions(
    days: int = 7,
    limit: int = 10,
    project_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Get most recent sessions with memory counts.

    Args:
        days: Look back N days (default 7).
        limit: Maximum sessions.
        project_path: Optional project filter.

    Returns:
        Dict with recent sessions summary.
    """
    return get_session_report(
        limit=limit,
        project_path=project_path,
        since_days=days,
        include_empty=False,
    )


def today_summary() -> Dict[str, Any]:
    """Get summary of today's activity.

    Returns:
        Dict with today's memories and sessions.
    """
    db = MemoryDatabase()
    try:
        # Start of today (midnight)
        now = time.time()
        today_start = now - (now % 86400)  # Round down to midnight UTC

        # Count today's memories
        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE created_at >= ?", (today_start,)
        )
        new_memories = cursor.fetchone()[0]

        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE updated_at >= ? AND created_at < ?",
            (today_start, today_start),
        )
        updated_memories = cursor.fetchone()[0]

        # Count today's sessions
        cursor = db.conn.execute(
            "SELECT COUNT(DISTINCT source_session_id) FROM memories WHERE created_at >= ?",
            (today_start,),
        )
        active_sessions = cursor.fetchone()[0]

        # Get recent memories (last 5)
        cursor = db.conn.execute(
            """
            SELECT id, content, tags, updated_at 
            FROM memories 
            WHERE updated_at >= ?
            ORDER BY updated_at DESC 
            LIMIT 5
        """,
            (today_start,),
        )

        recent = []
        for row in cursor:
            recent.append(
                {
                    "id": row["id"],
                    "preview": row["content"][:100] + "..."
                    if len(row["content"]) > 100
                    else row["content"],
                    "tags": row["tags"].split(",") if row["tags"] else [],
                }
            )

        # Get total stats
        cursor = db.conn.execute("SELECT COUNT(*) FROM memories")
        total_memories = cursor.fetchone()[0]

        return {
            "date": time.strftime("%Y-%m-%d"),
            "today": {
                "new_memories": new_memories,
                "updated_memories": updated_memories,
                "active_sessions": active_sessions,
            },
            "recent_memories": recent,
            "total_memories": total_memories,
        }

    finally:
        db.close()


def find_by_tag(
    tag: str,
    limit: int = 20,
    compact: bool = True,
) -> Dict[str, Any]:
    """Find memories by a specific tag.

    Args:
        tag: Tag to search for.
        limit: Maximum results.
        compact: If True, return compact format.

    Returns:
        Dict with matching memories.
    """
    db = MemoryDatabase()
    try:
        cursor = db.conn.execute(
            """
            SELECT id, content, tags, importance, project_path, updated_at
            FROM memories
            WHERE tags LIKE ?
            AND (superseded_by IS NULL OR superseded_by = '')
            ORDER BY updated_at DESC
            LIMIT ?
        """,
            (f"%{tag}%", limit),
        )

        memories = []
        for row in cursor:
            if compact:
                memories.append(
                    {
                        "id": row["id"],
                        "preview": row["content"][:150] + "..."
                        if len(row["content"]) > 150
                        else row["content"],
                        "tags": row["tags"].split(",") if row["tags"] else [],
                    }
                )
            else:
                memories.append(
                    {
                        "id": row["id"],
                        "content": row["content"],
                        "tags": row["tags"].split(",") if row["tags"] else [],
                        "importance": row["importance"],
                        "project_path": row["project_path"],
                        "updated_at": row["updated_at"],
                    }
                )

        return {
            "tag": tag,
            "memories": memories,
            "total": len(memories),
        }

    finally:
        db.close()


def list_all_tags(limit: int = 50) -> Dict[str, Any]:
    """List all unique tags with counts.

    Args:
        limit: Maximum tags to return.

    Returns:
        Dict with tag list and counts.
    """
    db = MemoryDatabase()
    try:
        cursor = db.conn.execute("""
            SELECT tags FROM memories 
            WHERE tags IS NOT NULL AND tags != ''
            AND (superseded_by IS NULL OR superseded_by = '')
        """)

        tag_counts: Dict[str, int] = {}
        for row in cursor:
            tags = row["tags"].split(",")
            for tag in tags:
                tag = tag.strip()
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by count descending
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))[:limit]

        return {
            "tags": [{"tag": t, "count": c} for t, c in sorted_tags],
            "total_unique": len(tag_counts),
            "showing": len(sorted_tags),
        }

    finally:
        db.close()
