"""List command for GMemory - lightweight memory listing without search."""

from typing import Dict, Any, Optional, List as ListType

from gmemory.storage.database import MemoryDatabase


def list_memories(
    limit: int = 20,
    offset: int = 0,
    project_path: Optional[str] = None,
    importance: Optional[str] = None,
    memory_type: Optional[str] = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
) -> Dict[str, Any]:
    """
    List memories without requiring a search query.

    This is the lightweight "overview" layer for progressive disclosure:
    1. list → browse all memories (no embedding needed)
    2. search --compact → semantic search with previews
    3. get <ids> → full content

    Args:
        limit: Maximum number of results to return.
        offset: Number of results to skip (for pagination).
        project_path: Optional project path to filter by.
        importance: Optional importance level to filter by (high/medium/low).
        memory_type: Optional memory type to filter by.
        sort_by: Field to sort by (created_at, updated_at). Defaults to updated_at.
        sort_order: Sort order (asc, desc). Defaults to desc.

    Returns:
        Dict containing:
        - results: List of memory summaries (id, tags, preview, importance, timestamps)
        - total: Total count of matching memories
        - has_more: Whether more results are available
    """
    db = None
    try:
        db = MemoryDatabase()

        # Build query
        conditions = []
        params: ListType = []

        if project_path:
            conditions.append("project_path = ?")
            params.append(project_path)

        if importance:
            conditions.append("importance = ?")
            params.append(importance)

        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Validate sort parameters
        valid_sort_fields = {"created_at", "updated_at", "importance"}
        if sort_by not in valid_sort_fields:
            sort_by = "updated_at"
        sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM memories {where_clause}"
        cursor = db.conn.execute(count_query, params)
        total = cursor.fetchone()[0]

        # Get paginated results
        query = f"""
            SELECT id, content, preview, tags, importance, memory_type, project_name, created_at, updated_at
            FROM memories
            {where_clause}
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor = db.conn.execute(query, params)

        results = []
        for row in cursor:
            content = row["content"]
            stored_preview = (row["preview"] or "").strip()
            if stored_preview:
                preview = stored_preview
            else:
                preview = content[:150] + "..." if len(content) > 150 else content

            # Parse tags
            tags_raw = row["tags"]
            if isinstance(tags_raw, str):
                import json

                try:
                    tags = json.loads(tags_raw)
                except json.JSONDecodeError:
                    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            else:
                tags = tags_raw or []

            results.append(
                {
                    "id": row["id"],
                    "tags": tags,
                    "preview": preview,
                    "importance": row["importance"],
                    "memory_type": row["memory_type"],
                    "project_name": row["project_name"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )

        return {
            "results": results,
            "total": total,
            "has_more": offset + len(results) < total,
        }

    finally:
        if db:
            db.close()
