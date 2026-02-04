"""Session aggregation report command for GMemory.

Provides session-level aggregation views for manual workflow efficiency.
Inspired by memex's session-level result grouping pattern.
"""

import time
from typing import Dict, Any, List, Optional
from collections import defaultdict

from gmemory.storage.database import MemoryDatabase


def get_session_report(
    limit: int = 20,
    project_path: Optional[str] = None,
    include_empty: bool = False,
    since_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate a session-level aggregation report.

    Groups memories by source_session_id and provides summary statistics
    for each session. This helps users understand memory distribution
    and identify sessions that may need review.

    Args:
        limit: Maximum number of sessions to return.
        project_path: Optional filter by project path.
        include_empty: Include sessions with no memories (from processed_sessions).
        since_days: Only include sessions from the last N days.

    Returns:
        Dict containing:
        - sessions: List of session summaries with memory counts and metadata
        - total_sessions: Total number of sessions found
        - total_memories: Total memories across all sessions
        - orphan_memories: Memories without session association
    """
    db = MemoryDatabase()
    try:
        # Build time filter
        time_filter = None
        if since_days:
            time_filter = int(time.time()) - (since_days * 24 * 3600)

        # Get all memories grouped by session
        query = """
            SELECT 
                source_session_id,
                project_path,
                project_name,
                agent,
                COUNT(*) as memory_count,
                GROUP_CONCAT(DISTINCT tags) as all_tags,
                MIN(created_at) as first_memory_at,
                MAX(updated_at) as last_updated_at,
                SUM(CASE WHEN importance = 'high' THEN 1 ELSE 0 END) as high_importance,
                SUM(CASE WHEN importance = 'medium' THEN 1 ELSE 0 END) as medium_importance,
                SUM(CASE WHEN importance = 'low' THEN 1 ELSE 0 END) as low_importance,
                SUM(CASE WHEN superseded_by IS NOT NULL THEN 1 ELSE 0 END) as superseded_count
            FROM memories
            WHERE 1=1
        """
        params: List[Any] = []

        if project_path:
            query += " AND project_path = ?"
            params.append(project_path)

        if time_filter:
            query += " AND created_at >= ?"
            params.append(time_filter)

        query += """
            GROUP BY source_session_id
            ORDER BY last_updated_at DESC
            LIMIT ?
        """
        params.append(limit * 2)  # Fetch extra for filtering

        cursor = db.conn.execute(query, params)
        rows = cursor.fetchall()

        sessions = []
        orphan_count = 0
        total_memories = 0

        for row in rows:
            session_id = row[0]
            memory_count = row[4]
            total_memories += memory_count

            if session_id is None:
                orphan_count = memory_count
                continue

            # Parse tags from concatenated string
            all_tags_str = row[5] or ""
            unique_tags = set()
            for tag_group in all_tags_str.split(","):
                tag_group = tag_group.strip()
                if tag_group.startswith("[") and tag_group.endswith("]"):
                    # JSON array format
                    import json

                    try:
                        tags = json.loads(tag_group)
                        unique_tags.update(tags)
                    except json.JSONDecodeError:
                        unique_tags.add(tag_group)
                elif tag_group:
                    unique_tags.add(tag_group)

            session_summary = {
                "session_id": session_id,
                "project_path": row[1],
                "project_name": row[2],
                "agent": row[3],
                "memory_count": memory_count,
                "tags": sorted(list(unique_tags))[:10],  # Top 10 tags
                "tag_count": len(unique_tags),
                "first_memory_at": row[6],
                "last_updated_at": row[7],
                "importance_breakdown": {
                    "high": row[8] or 0,
                    "medium": row[9] or 0,
                    "low": row[10] or 0,
                },
                "superseded_count": row[11] or 0,
                "active_memories": memory_count - (row[11] or 0),
            }
            sessions.append(session_summary)

            if len(sessions) >= limit:
                break

        # Include empty sessions if requested
        if include_empty:
            # Get processed sessions that have no memories
            existing_session_ids = {s["session_id"] for s in sessions}
            empty_query = """
                SELECT session_id, agent, processed_at
                FROM processed_sessions
                WHERE session_id NOT IN (
                    SELECT DISTINCT source_session_id 
                    FROM memories 
                    WHERE source_session_id IS NOT NULL
                )
            """
            if time_filter:
                empty_query += " AND processed_at >= ?"
                cursor = db.conn.execute(empty_query, (time_filter,))
            else:
                cursor = db.conn.execute(empty_query)

            for row in cursor:
                if row[0] not in existing_session_ids and len(sessions) < limit:
                    sessions.append(
                        {
                            "session_id": row[0],
                            "agent": row[1],
                            "processed_at": row[2],
                            "memory_count": 0,
                            "tags": [],
                            "tag_count": 0,
                            "importance_breakdown": {"high": 0, "medium": 0, "low": 0},
                            "superseded_count": 0,
                            "active_memories": 0,
                            "is_empty": True,
                        }
                    )

        return {
            "sessions": sessions,
            "total_sessions": len(sessions),
            "total_memories": total_memories,
            "orphan_memories": orphan_count,
            "filters": {
                "project_path": project_path,
                "since_days": since_days,
                "include_empty": include_empty,
            },
        }

    finally:
        db.close()


def get_session_detail(
    session_id: str,
    include_content: bool = False,
) -> Dict[str, Any]:
    """Get detailed information about a specific session.

    Args:
        session_id: The session ID to look up.
        include_content: If True, include full memory content (can be large).

    Returns:
        Dict containing session details and associated memories.
    """
    db = MemoryDatabase()
    try:
        # Get all memories for this session
        cursor = db.conn.execute(
            """
            SELECT * FROM memories
            WHERE source_session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        )
        rows = cursor.fetchall()

        if not rows:
            # Check if session exists in processed_sessions
            cursor = db.conn.execute(
                "SELECT * FROM processed_sessions WHERE session_id = ?",
                (session_id,),
            )
            processed = cursor.fetchone()
            if processed:
                return {
                    "session_id": session_id,
                    "found": True,
                    "processed_at": processed["processed_at"],
                    "agent": processed["agent"],
                    "memories": [],
                    "memory_count": 0,
                    "is_empty": True,
                }
            return {
                "session_id": session_id,
                "found": False,
                "error": "Session not found in memories or processed_sessions",
            }

        # Aggregate session info
        import json

        memories = []
        all_tags = set()
        importance_counts = {"high": 0, "medium": 0, "low": 0}

        for row in rows:
            row_dict = dict(row)
            tags = row_dict.get("tags", "[]")
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except json.JSONDecodeError:
                    tags = []
            all_tags.update(tags)

            importance = row_dict.get("importance", "medium")
            if importance in importance_counts:
                importance_counts[importance] += 1

            memory_entry = {
                "id": row_dict["id"],
                "tags": tags,
                "importance": importance,
                "created_at": row_dict["created_at"],
                "updated_at": row_dict["updated_at"],
                "superseded_by": row_dict.get("superseded_by"),
            }

            if include_content:
                memory_entry["content"] = row_dict["content"]
            else:
                content = row_dict["content"]
                memory_entry["preview"] = (
                    content[:150] + "..." if len(content) > 150 else content
                )
                memory_entry["content_length"] = len(content)

            memories.append(memory_entry)

        first_row = dict(rows[0])
        return {
            "session_id": session_id,
            "found": True,
            "project_path": first_row.get("project_path"),
            "project_name": first_row.get("project_name"),
            "agent": first_row.get("agent"),
            "memory_count": len(memories),
            "active_memories": sum(1 for m in memories if not m.get("superseded_by")),
            "tags": sorted(list(all_tags)),
            "importance_breakdown": importance_counts,
            "first_memory_at": memories[0]["created_at"] if memories else None,
            "last_updated_at": memories[-1]["updated_at"] if memories else None,
            "memories": memories,
        }

    finally:
        db.close()
