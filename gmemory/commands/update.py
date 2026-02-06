import time
from typing import List, Optional, Dict, Any, Union
from gmemory.storage.database import MemoryDatabase
from gmemory.storage.embedder import get_embedder, NoOpEmbedder, is_valid_embedding
from gmemory.config import config


def update_memory(
    mem_id: str,
    content: str,
    preview: str,
    tags: Optional[Union[List[str], str]] = None,
    importance: Optional[str] = None,
    memory_type: Optional[str] = None,
    project_path: Optional[str] = None,
    project_name: Optional[str] = None,
    require_embedding: bool = True,
) -> Dict[str, Any]:
    """
    Update an existing memory in the database.

    Args:
        mem_id: The ID of the memory to update.
        content: The new text content of the memory.
        preview: Agent-provided preview text (required, not auto-generated).
        tags: List of tags or comma-separated string of tags.
        importance: Importance level (low, medium, high).
        memory_type: Type of memory (observation, fact, pattern).
        project_path: Path to the project.
        project_name: Name of the project.
        require_embedding: If True and content changed, fail when embedding unavailable.

    Returns:
        Dict containing:
        - id: The ID of the updated memory.
        - updated: Boolean indicating success.
        - preview: Agent-provided preview text.

    Raises:
        ValueError: If memory with mem_id is not found.
    """
    db = None
    try:
        if not preview or not preview.strip():
            return {
                "id": mem_id,
                "updated": False,
                "error": "preview is required and cannot be empty",
            }

        db = MemoryDatabase()
        memory = db.get_memory(mem_id)

        if not memory:
            raise ValueError(f"Memory with ID {mem_id} not found.")

        # Update fields if provided
        memory.content = content
        memory.preview = preview

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
        embedding_stored = False
        error_msg = None
        embedder = None

        try:
            embedder = get_embedder()
            if isinstance(embedder, NoOpEmbedder):
                error_msg = "Embedding service unavailable"
            else:
                embedding = embedder.embed(content)
                if is_valid_embedding(embedding, config.embedding_dimension):
                    embedding_stored = True
                else:
                    error_msg = f"Invalid embedding dimension (expected {config.embedding_dimension})"
                    embedding = None
        except Exception as e:
            error_msg = f"Embedding failed: {str(e)}"

        # Block update if embedding required but unavailable
        if require_embedding and not embedding_stored:
            return {
                "id": mem_id,
                "updated": False,
                "error": error_msg or "Embedding required but not available",
            }

        # Generate tag embedding if tag index is enabled and tags changed or content changed
        tag_embedding = None
        should_update_tag_index = (
            config.search_use_tag_index
            and memory.tags
            and (tags is not None or bool(content))
        )
        if should_update_tag_index:
            try:
                if embedder is None:
                    embedder = get_embedder()
                if not isinstance(embedder, NoOpEmbedder):
                    tag_text = ", ".join(memory.tags)
                    tag_embedding = embedder.embed(tag_text)
                    if not is_valid_embedding(
                        tag_embedding, config.embedding_dimension
                    ):
                        tag_embedding = None
            except Exception:
                pass  # Tag embedding is optional, don't fail on error

        # Save updates
        db.update_memory(
            memory,
            embedding if embedding_stored else None,
            tag_embedding=tag_embedding,
        )

        result = {
            "id": mem_id,
            "updated": True,
            "preview": preview,
        }
        if error_msg and not require_embedding:
            result["warning"] = error_msg

        return result

    except Exception as e:
        raise e
    finally:
        if db:
            db.close()
