"""Quick access commands for GMemory.

Provides shortcut commands for common high-frequency operations
to reduce typing and improve CLI ergonomics.
"""

import time
from typing import Any, Dict, List, Optional

from gmemory.commands.search import search_memories
from gmemory.commands.session_report import get_session_report
from gmemory.container import get_container


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
    container = get_container()
    db = container.get_database()

    memories = db.get_recent_memories(
        days=days,
        limit=limit,
        project_path=project_path,
        tags=tags,
    )

    cutoff = time.time() - (days * 24 * 3600)

    return {
        "memories": memories,
        "total": len(memories),
        "days": days,
        "cutoff_timestamp": cutoff,
    }


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
    container = get_container()
    db = container.get_database()

    return db.get_today_stats()


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
    container = get_container()
    db = container.get_database()

    memories_data = db.find_memories_by_tag(tag=tag, limit=limit)

    memories = []
    for mem in memories_data:
        if compact:
            memories.append(
                {
                    "id": mem["id"],
                    "preview": mem["preview"],
                    "tags": mem["tags"],
                }
            )
        else:
            memories.append(
                {
                    "id": mem["id"],
                    "content": mem["content"],
                    "tags": mem["tags"],
                    "importance": mem["importance"],
                    "project_path": mem["project_path"],
                    "updated_at": mem["updated_at"],
                }
            )

    return {
        "tag": tag,
        "memories": memories,
        "total": len(memories),
    }


def list_all_tags(limit: int = 50) -> Dict[str, Any]:
    """List all unique tags with counts.

    Args:
        limit: Maximum tags to return.

    Returns:
        Dict with tag list and counts.
    """
    container = get_container()
    db = container.get_database()

    sorted_tags = db.get_all_tags(limit=limit)

    # Get total unique count (may be more than limit)
    all_tags = db.get_all_tags(limit=10000)
    total_unique = len(all_tags)

    return {
        "tags": [{"tag": t, "count": c} for t, c in sorted_tags],
        "total_unique": total_unique,
        "showing": len(sorted_tags),
    }
