import time
from typing import List, Optional, Dict, Any, Union
from gmemory.storage.database import MemoryDatabase
from gmemory.storage.embedder import get_embedder, NoOpEmbedder


def update_memory(
    mem_id: str,
    content: Optional[str] = None,
    tags: Optional[Union[List[str], str]] = None,
    importance: Optional[str] = None,
    memory_type: Optional[str] = None,
    project_path: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update an existing memory in the database.

    Args:
        mem_id: The ID of the memory to update.
        content: The new text content of the memory.
        tags: List of tags or comma-separated string of tags.
        importance: Importance level (low, medium, high).
        memory_type: Type of memory (observation, fact, pattern).
        project_path: Path to the project.
        project_name: Name of the project.

    Returns:
        Dict containing:
        - id: The ID of the updated memory.
        - updated: Boolean indicating success.

    Raises:
        ValueError: If memory with mem_id is not found.
    """
    db = None
    try:
        db = MemoryDatabase()
        memory = db.get_memory(mem_id)

        if not memory:
            raise ValueError(f"Memory with ID {mem_id} not found.")

        # Update fields if provided
        if content is not None:
            memory.content = content

        if tags is not None:
            if isinstance(tags, str):
                memory.tags = [t.strip() for t in tags.split(",") if t.strip()]
            else:
                memory.tags = tags

        if importance is not None:
            memory.importance = importance

        if memory_type is not None:
            memory.memory_type = memory_type

        if project_path is not None:
            memory.project_path = project_path

        if project_name is not None:
            memory.project_name = project_name

        # Regenerate embedding if content changed
        embedding = None
        warning_msg = None

        if content is not None:
            try:
                embedder = get_embedder()
                if isinstance(embedder, NoOpEmbedder):
                    warning_msg = "Embedding service unavailable"
                else:
                    embedding = embedder.embed(content)
            except Exception as e:
                warning_msg = f"Embedding failed: {str(e)}"

        # Save updates
        # Note: MemoryDatabase.update_memory handles updating the updated_at timestamp
        db.update_memory(memory, embedding)

        result = {
            "id": mem_id,
            "updated": True,
        }
        if warning_msg:
            result["warning"] = warning_msg

        return result

    except Exception as e:
        raise e
    finally:
        if db:
            db.close()
