import uuid
import time
from typing import List, Optional, Dict, Any, Union
from gmemory.models import Memory, ProcessedSession
from gmemory.storage.database import MemoryDatabase
from gmemory.storage.embedder import get_embedder, NoOpEmbedder, is_valid_embedding
from gmemory.config import config


def save_memory(
    session_id: str,
    content: str,
    tags: Optional[Union[List[str], str]] = None,
    importance: str = "medium",
    memory_type: Optional[str] = None,
    agent: Optional[str] = None,
    project_path: Optional[str] = None,
    project_name: Optional[str] = None,
    require_embedding: bool = True,
) -> Dict[str, Any]:
    """
    Save a distilled memory and mark the source session as processed.

    Args:
        session_id: The ID of the session the memory is derived from.
        content: The text content of the memory.
        tags: List of tags or comma-separated string of tags. Defaults to empty list.
        importance: Importance level (low, medium, high). Defaults to "medium".
        memory_type: Type of memory (observation, fact, pattern). Defaults to "observation".
        agent: The agent identifier. Defaults to config.default_agent.
        project_path: Path to the project.
        project_name: Name of the project.
        require_embedding: If True, fail when embedding is unavailable. Defaults to True.

    Returns:
        Dict containing:
        - memory_id: The ID of the created memory.
        - created: Boolean indicating success.
        - session_marked: Boolean indicating if the session was marked as processed.
        - embedding_stored: Boolean indicating if embedding was stored.
    """
    # Resolve agent
    if not agent:
        agent = config.default_agent

    # Normalize tags
    if tags is None:
        tags_list: List[str] = []
    elif isinstance(tags, str):
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    else:
        tags_list = tags

    # Default memory_type
    if memory_type is None:
        memory_type = "observation"

    # Generate Memory ID
    memory_id = str(uuid.uuid4())
    current_time = int(time.time())

    # Create Memory object
    memory = Memory(
        id=memory_id,
        content=content,
        tags=tags_list,
        importance=importance,
        memory_type=memory_type,
        agent=agent,
        source_session_id=session_id,
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
                "memory_id": None,
                "created": False,
                "session_marked": False,
                "embedding_stored": False,
                "error": error_msg or "Embedding required but not available",
            }

        # Initialize Database
        db = MemoryDatabase()

        # Save Memory
        db.add_memory(memory, embedding if embedding_stored else None)

        # Mark Session as Processed
        processed_session = ProcessedSession(
            agent=agent,
            session_id=session_id,
            processed_at=current_time,
        )
        db.add_processed_session(processed_session)

        result = {
            "memory_id": memory_id,
            "created": True,
            "session_marked": True,
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
