import uuid
import time
from typing import List, Optional, Dict, Any, Union
from gmemory.models import Memory
from gmemory.storage.database import MemoryDatabase
from gmemory.storage.embedder import get_embedder, NoOpEmbedder, is_valid_embedding
from gmemory.config import config


def add_memory(
    content: str,
    tags: Union[List[str], str],
    importance: str = "medium",
    memory_type: str = "observation",
    agent: Optional[str] = None,
    project_path: Optional[str] = None,
    project_name: Optional[str] = None,
    require_embedding: bool = True,
) -> Dict[str, Any]:
    """
    Manually add a memory to the database.

    Args:
        content: The text content of the memory.
        tags: List of tags or comma-separated string of tags.
        importance: Importance level (low, medium, high). Defaults to "medium".
        memory_type: Type of memory (observation, fact, pattern). Defaults to "observation".
        agent: The agent identifier. Defaults to config.default_agent.
        project_path: Path to the project.
        project_name: Name of the project.
        require_embedding: If True, fail when embedding is unavailable. Defaults to True.

    Returns:
        Dict containing:
        - id: The ID of the created memory.
        - created: Boolean indicating success.
        - embedding_stored: Boolean indicating if embedding was stored.
    """
    # Resolve agent
    if not agent:
        agent = config.default_agent

    # Normalize tags
    if isinstance(tags, str):
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    else:
        tags_list = tags

    # Generate Memory ID
    memory_id = str(uuid.uuid4())
    current_time = int(time.time())

    # Create Memory object
    # source_session_id is None for manually added memories
    memory = Memory(
        id=memory_id,
        content=content,
        tags=tags_list,
        importance=importance,
        memory_type=memory_type,
        agent=agent,
        source_session_id=None,
        project_path=project_path,
        project_name=project_name,
        created_at=current_time,
        updated_at=current_time,
    )

    db = None
    try:
        # Generate embedding
        embedding = None
        embedding_stored = False
        error_msg = None

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

        # Block write if embedding required but unavailable
        if require_embedding and not embedding_stored:
            return {
                "id": None,
                "created": False,
                "embedding_stored": False,
                "error": error_msg or "Embedding required but not available",
            }

        # Initialize Database
        db = MemoryDatabase()

        # Save Memory (only with valid embedding or if not required)
        db.add_memory(memory, embedding if embedding_stored else None)

        result = {
            "id": memory_id,
            "created": True,
            "embedding_stored": embedding_stored,
        }
        if error_msg and not require_embedding:
            result["warning"] = error_msg

        return result

    except Exception as e:
        raise e
    finally:
        if db:
            db.close()
