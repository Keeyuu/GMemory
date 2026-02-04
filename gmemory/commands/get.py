"""Get command for GMemory - retrieve full memory content by IDs."""

from typing import List, Dict, Any, Optional

from gmemory.storage.database import MemoryDatabase


def get_memories(
    ids: List[str],
    include_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Retrieve full memory content by IDs.

    This is the second layer of progressive disclosure:
    1. search --compact → get IDs and previews
    2. get <ids> → get full content

    Args:
        ids: List of memory IDs to retrieve.
        include_metadata: Include metadata (project, agent, timestamps).

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
                if include_metadata:
                    result = {
                        "id": memory.id,
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
                    }
                else:
                    result = {
                        "id": memory.id,
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
