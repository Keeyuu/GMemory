from typing import List, Optional, Dict, Any, Union
from gmemory.storage.database import MemoryDatabase
from gmemory.storage.embedder import get_embedder, NoOpEmbedder


def search_memories(
    query: str,
    project_path: Optional[str] = None,
    tags: Optional[Union[List[str], str]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search for memories using vector similarity and metadata filtering.

    Args:
        query: The search query string.
        project_path: Optional project path to filter by.
        tags: Optional list of tags or comma-separated string to filter by (memory must contain all tags).
        limit: Maximum number of results to return.

    Returns:
        Dict containing:
        - results: List of result dictionaries (id, content, tags, similarity, etc.)
        - total: Number of results returned
    """
    # Normalize tags: support both list and comma-separated string
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

    # 1. Generate embedding for the query
    try:
        embedder = get_embedder()
        if isinstance(embedder, NoOpEmbedder):
            return {
                "results": [],
                "total": 0,
                "warning": "Embedding service unavailable",
            }
        query_embedding = embedder.embed(query)
    except Exception as e:
        return {"results": [], "total": 0, "warning": f"Embedding failed: {str(e)}"}

    # 2. Search in database
    # We request more results than the limit to allow for post-filtering
    # Fetch factor * limit, but at least 50 to have a good pool
    fetch_limit = max(50, limit * 5)

    db = MemoryDatabase()
    try:
        # returns List[Tuple[Memory, distance]]
        # Note: database.py search_memories applies a default similarity threshold of 0.5
        candidates = db.search_memories(query_embedding, limit=fetch_limit)
    finally:
        db.close()

    results = []

    # 3. Apply post-filtering
    for memory, distance in candidates:
        # Filter by project_path
        if project_path:
            # Check for exact match or if memory path is a subdirectory?
            # For simplicity and strictness, we'll use exact match as per current metadata usage.
            # If the user provides a path, they likely want memories associated with that specific project root.
            if memory.project_path != project_path:
                continue

        # Filter by tags
        if tags:
            memory_tags = set(memory.tags)
            required_tags = set(tags)
            # We require the memory to have ALL the requested tags
            if not required_tags.issubset(memory_tags):
                continue

        # Calculate similarity (assuming distance is cosine distance)
        similarity = 1.0 - distance

        # Format result
        result = {
            "id": memory.id,
            "content": memory.content,
            "tags": memory.tags,
            "similarity": similarity,
            "project_path": memory.project_path,
            "agent": memory.agent,
            "created_at": memory.created_at,
        }
        results.append(result)

        # Stop if we hit the limit
        if len(results) >= limit:
            break

    return {"results": results, "total": len(results)}
