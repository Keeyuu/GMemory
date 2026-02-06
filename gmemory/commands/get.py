"""Get command for GMemory - retrieve full memory content by IDs."""

import time
from typing import List, Dict, Any, Optional

from gmemory.storage.database import MemoryDatabase


def _resolve_preview(preview: Optional[str], content: str, max_len: int = 180) -> str:
    """Resolve preview with backward-compatible fallback for legacy memories."""
    normalized_preview = (preview or "").strip()
    if normalized_preview:
        return normalized_preview

    normalized_content = (content or "").replace("\n", " ").strip()
    if len(normalized_content) <= max_len:
        return normalized_content
    return f"{normalized_content[:max_len]}..."


def get_memories(
    ids: List[str],
    include_metadata: bool = True,
    track_access: bool = True,
) -> Dict[str, Any]:
    """
    Retrieve full memory content by IDs.

    This is the second layer of progressive disclosure:
    1. search --compact → get IDs and previews
    2. get <ids> → get full content

    Args:
        ids: List of memory IDs to retrieve.
        include_metadata: Include metadata (project, agent, timestamps).
        track_access: If True, increment access count for each found memory.

    Returns:
        Dict containing:
        - results: List of memory dictionaries
        - found: Number of memories found
        - missing: List of IDs not found
    """
    if not ids:
        return {"results": [], "found": 0, "missing": []}

    db = MemoryDatabase()
    try:
        results = []
        missing = []

        for memory_id in ids:
            memory = db.get_memory(memory_id)
            if memory:
                access_count = memory.access_count
                last_accessed_at = memory.last_accessed_at
                if track_access:
                    if db.touch_memory_access(memory_id):
                        access_count += 1
                        # Avoid opening another read transaction just for response metadata.
                        last_accessed_at = int(time.time())

                preview = _resolve_preview(memory.preview, memory.content)
                if include_metadata:
                    result = {
                        "id": memory.id,
                        "preview": preview,
                        "content": memory.content,
                        "tags": memory.tags,
                        "importance": memory.importance,
                        "memory_type": memory.memory_type,
                        "project_path": memory.project_path,
                        "project_name": memory.project_name,
                        "agent": memory.agent,
                        "source_session_id": memory.source_session_id,
                        "created_at": memory.created_at,
                        "updated_at": memory.updated_at,
                        "access_count": access_count,
                        "last_accessed_at": last_accessed_at,
                    }
                else:
                    result = {
                        "id": memory.id,
                        "preview": preview,
                        "content": memory.content,
                        "tags": memory.tags,
                    }
                results.append(result)
            else:
                missing.append(memory_id)

        return {
            "results": results,
            "found": len(results),
            "missing": missing if missing else None,
        }
    finally:
        db.close()


def get_memory_by_id(memory_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single memory by ID.

    Args:
        memory_id: The memory ID to retrieve.

    Returns:
        Memory dict or None if not found.
    """
    result = get_memories([memory_id])
    if result["results"]:
        return result["results"][0]
    return None
