"""Search command for GMemory."""

import time
from typing import List, Optional, Dict, Any, Union

from gmemory.storage.database import MemoryDatabase
from gmemory.storage.embedder import get_embedder, NoOpEmbedder, is_valid_embedding
from gmemory.config import config


def search_memories(
    query: str,
    project_path: Optional[str] = None,
    tags: Optional[Union[List[str], str]] = None,
    limit: int = 10,
    compact: bool = False,
    mode: str = "hybrid",
    recency_weight: float = 0.0,
    include_superseded: bool = False,
) -> Dict[str, Any]:
    """
    Search for memories using hybrid (vector + FTS) or vector-only search.

    Args:
        query: The search query string.
        project_path: Optional project path to filter by.
        tags: Optional list of tags or comma-separated string to filter by (memory must contain all tags).
        limit: Maximum number of results to return.
        compact: If True, return compact results (id, tags, preview only).
        mode: Search mode - "hybrid" (default), "vector", or "fts".
        recency_weight: Weight for recency boost (0.0-1.0). 0.0 = no boost (default),
                        1.0 = heavily favor recent memories. The final score is:
                        (1 - recency_weight) * similarity + recency_weight * recency_score
        include_superseded: If True, include memories that have been superseded.

    Returns:
        Dict containing:
        - results: List of result dictionaries
        - total: Number of results returned
        - mode: Search mode used
        - warning/error: Optional message if search quality is degraded
    """
    # Normalize tags: support both list and comma-separated string
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

    # Clamp recency_weight to valid range
    recency_weight = max(0.0, min(1.0, recency_weight))

    db = MemoryDatabase()
    try:
        # FTS-only mode (no embedding needed)
        if mode == "fts":
            return _search_fts_only(
                db,
                query,
                project_path,
                tags,
                limit,
                compact,
                recency_weight=recency_weight,
                include_superseded=include_superseded,
            )

        # Vector or hybrid mode - need embedding
        try:
            embedder = get_embedder()
            if isinstance(embedder, NoOpEmbedder):
                # Fall back to FTS-only
                return _search_fts_only(
                    db,
                    query,
                    project_path,
                    tags,
                    limit,
                    compact,
                    warning="Embedding unavailable, using FTS-only search.",
                    recency_weight=recency_weight,
                    include_superseded=include_superseded,
                )
            query_embedding = embedder.embed(query)

            # Validate the embedding
            if not is_valid_embedding(query_embedding, config.embedding_dimension):
                return _search_fts_only(
                    db,
                    query,
                    project_path,
                    tags,
                    limit,
                    compact,
                    warning="Invalid embedding, using FTS-only search.",
                    recency_weight=recency_weight,
                    include_superseded=include_superseded,
                )
        except Exception as e:
            return _search_fts_only(
                db,
                query,
                project_path,
                tags,
                limit,
                compact,
                warning=f"Embedding failed ({e}), using FTS-only search.",
                recency_weight=recency_weight,
                include_superseded=include_superseded,
            )

        # Perform search based on mode
        fetch_limit = max(50, limit * 5)

        if mode == "hybrid":
            candidates = db.hybrid_search(
                query_embedding, query, limit=fetch_limit, threshold=0.2
            )
            # hybrid_search returns (Memory, combined_score) where score is similarity
            candidates = [
                (m, 1.0 - s) for m, s in candidates
            ]  # Convert to distance for consistency
        else:  # vector mode
            candidates = db.search_memories(query_embedding, limit=fetch_limit)

        results = _filter_and_format(
            candidates,
            project_path,
            tags,
            limit,
            compact,
            recency_weight=recency_weight,
            include_superseded=include_superseded,
        )
        return {"results": results, "total": len(results), "mode": mode}

    finally:
        db.close()


def _search_fts_only(
    db: MemoryDatabase,
    query: str,
    project_path: Optional[str],
    tags: Optional[List[str]],
    limit: int,
    compact: bool,
    warning: Optional[str] = None,
    recency_weight: float = 0.0,
    include_superseded: bool = False,
) -> Dict[str, Any]:
    """Perform FTS-only search."""
    fetch_limit = max(50, limit * 5)
    fts_results = db.search_fts(query, limit=fetch_limit)

    if not fts_results:
        result = {"results": [], "total": 0, "mode": "fts"}
        if warning:
            result["warning"] = warning
        return result

    # Fetch memories and convert to candidate format
    candidates = []
    for memory_id, score in fts_results:
        memory = db.get_memory(memory_id)
        if memory:
            # Normalize BM25 score to distance-like value (lower is better)
            # BM25 is negative, so we use abs and normalize
            candidates.append((memory, abs(score) / 100.0))

    results = _filter_and_format(
        candidates,
        project_path,
        tags,
        limit,
        compact,
        recency_weight=recency_weight,
        include_superseded=include_superseded,
    )
    result = {"results": results, "total": len(results), "mode": "fts"}
    if warning:
        result["warning"] = warning
    return result


def _filter_and_format(
    candidates: List,
    project_path: Optional[str],
    tags: Optional[List[str]],
    limit: int,
    compact: bool,
    recency_weight: float = 0.0,
    include_superseded: bool = False,
) -> List[Dict[str, Any]]:
    """Apply post-filtering, recency weighting, and format results.

    Args:
        candidates: List of (Memory, distance) tuples.
        project_path: Optional project path filter.
        tags: Optional tags filter.
        limit: Maximum results to return.
        compact: Whether to return compact format.
        recency_weight: Weight for recency boost (0.0-1.0).
        include_superseded: Whether to include superseded memories.

    Returns:
        List of formatted result dictionaries.
    """
    now = time.time()
    # Define time window for recency calculation (90 days)
    recency_window = 90 * 24 * 3600  # 90 days in seconds

    filtered = []

    for memory, distance in candidates:
        # Filter out superseded memories unless explicitly requested
        if not include_superseded:
            # Check if memory has superseded_by attribute and it's set
            if hasattr(memory, "superseded_by") and memory.superseded_by:
                continue

        # Filter by project_path
        if project_path:
            if memory.project_path != project_path:
                continue

        # Filter by tags
        if tags:
            memory_tags = set(memory.tags)
            required_tags = set(tags)
            if not required_tags.issubset(memory_tags):
                continue

        # Calculate base similarity (assuming distance is cosine distance)
        similarity = 1.0 - distance

        # Calculate recency score (0.0 = old, 1.0 = recent)
        age = now - memory.updated_at
        recency_score = max(0.0, 1.0 - (age / recency_window))

        # Combine similarity and recency
        if recency_weight > 0:
            final_score = (
                1.0 - recency_weight
            ) * similarity + recency_weight * recency_score
        else:
            final_score = similarity

        filtered.append((memory, distance, similarity, final_score))

    # Sort by final score (descending) if recency is applied
    if recency_weight > 0:
        filtered.sort(key=lambda x: x[3], reverse=True)

    # Format results
    results = []
    for memory, distance, similarity, final_score in filtered:
        if compact:
            preview = (
                memory.content[:150] + "..."
                if len(memory.content) > 150
                else memory.content
            )
            result = {
                "id": memory.id,
                "tags": memory.tags,
                "preview": preview,
                "similarity": round(similarity, 3),
                "tokens": _estimate_tokens(memory.content),
            }
            if recency_weight > 0:
                result["score"] = round(final_score, 3)
        else:
            result = {
                "id": memory.id,
                "content": memory.content,
                "tags": memory.tags,
                "similarity": similarity,
                "project_path": memory.project_path,
                "agent": memory.agent,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
            }
            if recency_weight > 0:
                result["score"] = final_score

        results.append(result)

        if len(results) >= limit:
            break

    return results


def _estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars per token on average)."""
    return len(text) // 4
