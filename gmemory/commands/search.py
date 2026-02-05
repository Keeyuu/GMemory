"""Search command for GMemory."""

import time
from typing import List, Optional, Dict, Any, Union

from gmemory.container import get_container
from gmemory.storage.embedder import NoOpEmbedder, is_valid_embedding
from gmemory.commands.profiles import get_profile, SearchProfile, DEFAULT_PROFILE
from gmemory.ports import ConfigPort, DatabasePort, EmbedderPort


def search_memories(
    query: str,
    project_path: Optional[str] = None,
    tags: Optional[Union[List[str], str]] = None,
    limit: Optional[int] = None,
    compact: bool = False,
    mode: Optional[str] = None,
    recency_weight: Optional[float] = None,
    include_superseded: bool = False,
    explain: bool = False,
    use_tag_index: Optional[bool] = None,
    tag_weight: Optional[float] = None,
    profile: Optional[str] = None,
    min_score: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Search for memories using hybrid (vector + FTS) or vector-only search.

    Args:
        query: The search query string.
        project_path: Optional project path to filter by.
        tags: Optional list of tags or comma-separated string to filter by (memory must contain all tags).
        limit: Maximum number of results to return.
        compact: If True, return compact results (id, tags, preview only).
        mode: Search mode - "hybrid" (default), "vector", or "fts". Overrides profile.
        recency_weight: Weight for recency boost (0.0-1.0). Overrides profile.
        include_superseded: If True, include memories that have been superseded.
        explain: If True, include detailed scoring breakdown for each result.
        use_tag_index: If True, use dual vector index (content + tags) for search. Overrides profile.
        tag_weight: Weight for tag similarity when use_tag_index=True (0.0-1.0). Overrides profile.
        profile: Name of a search profile to use. Individual parameters override profile settings.

    Returns:
        Dict containing:
        - results: List of result dictionaries
        - total: Number of results returned
        - mode: Search mode used
        - profile: Profile name used (if any)
        - scoring_config: Scoring configuration used (if explain=True)
        - warning/error: Optional message if search quality is degraded
    """
    # Get dependencies from container
    container = get_container()
    cfg = container.get_config()
    db = container.get_database()

    # Resolve profile and apply settings
    active_profile: Optional[SearchProfile] = None
    if profile:
        active_profile = get_profile(profile)
        if not active_profile:
            return {
                "results": [],
                "total": 0,
                "error": f"Unknown profile: '{profile}'. Use 'gmemory profiles' to list available profiles.",
            }

    # Apply config defaults first, then profile, then CLI overrides
    effective_limit = limit if limit is not None else cfg.search_default_limit
    effective_min_score = (
        min_score if min_score is not None else cfg.search_min_score_threshold
    )

    # Apply profile defaults, then allow individual overrides
    if active_profile:
        effective_mode = mode if mode is not None else active_profile.mode
        effective_recency = (
            recency_weight
            if recency_weight is not None
            else active_profile.recency_weight
        )
        effective_use_tag_index = (
            use_tag_index if use_tag_index is not None else active_profile.use_tag_index
        )
        effective_tag_weight = (
            tag_weight if tag_weight is not None else active_profile.tag_weight
        )
    else:
        # Use config defaults when no profile specified
        effective_mode = mode if mode is not None else cfg.search_default_mode
        effective_recency = (
            recency_weight if recency_weight is not None else cfg.search_recency_weight
        )
        effective_use_tag_index = (
            use_tag_index if use_tag_index is not None else cfg.search_use_tag_index
        )
        effective_tag_weight = (
            tag_weight if tag_weight is not None else cfg.search_tag_weight
        )

    # Normalize tags: support both list and comma-separated string
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

    # Clamp recency_weight to valid range
    effective_recency = max(0.0, min(1.0, effective_recency))

    # Clamp tag_weight to valid range
    effective_tag_weight = max(0.0, min(1.0, effective_tag_weight))

    try:
        # FTS-only mode (no embedding needed)
        if effective_mode == "fts":
            result = _search_fts_only(
                db,
                cfg,
                query,
                project_path,
                tags,
                effective_limit,
                compact,
                recency_weight=effective_recency,
                include_superseded=include_superseded,
                explain=explain,
                min_score=effective_min_score,
            )
            if active_profile:
                result["profile"] = active_profile.name
            return result

        # Vector or hybrid mode - need embedding
        try:
            embedder = container.get_embedder()
            if isinstance(embedder, NoOpEmbedder):
                # Fall back to FTS-only
                result = _search_fts_only(
                    db,
                    cfg,
                    query,
                    project_path,
                    tags,
                    effective_limit,
                    compact,
                    warning="Embedding unavailable, using FTS-only search.",
                    recency_weight=effective_recency,
                    include_superseded=include_superseded,
                    explain=explain,
                    min_score=effective_min_score,
                )
                if active_profile:
                    result["profile"] = active_profile.name
                return result
            query_embedding = embedder.embed(query)

            # Validate the embedding
            if not is_valid_embedding(query_embedding, cfg.embedding_dimension):
                result = _search_fts_only(
                    db,
                    cfg,
                    query,
                    project_path,
                    tags,
                    effective_limit,
                    compact,
                    warning="Invalid embedding, using FTS-only search.",
                    recency_weight=effective_recency,
                    include_superseded=include_superseded,
                    explain=explain,
                    min_score=effective_min_score,
                )
                if active_profile:
                    result["profile"] = active_profile.name
                return result
        except Exception as e:
            result = _search_fts_only(
                db,
                cfg,
                query,
                project_path,
                tags,
                effective_limit,
                compact,
                warning=f"Embedding failed ({e}), using FTS-only search.",
                recency_weight=effective_recency,
                include_superseded=include_superseded,
                explain=explain,
                min_score=effective_min_score,
            )
            if active_profile:
                result["profile"] = active_profile.name
            return result

        # Perform search based on mode
        fetch_limit = max(50, effective_limit * 5)

        if effective_mode == "hybrid":
            # Use explainable hybrid search
            candidates = _hybrid_search_with_scores(
                db,
                query_embedding,
                query,
                fetch_limit,
                use_tag_index=effective_use_tag_index,
                tag_weight=effective_tag_weight,
            )
        else:  # vector mode
            vec_results = db.search_memories(query_embedding, limit=fetch_limit)
            # Convert to unified format with score breakdown
            candidates = []
            for memory, distance in vec_results:
                candidates.append(
                    {
                        "memory": memory,
                        "vec_score": 1.0 - distance,
                        "fts_score": 0.0,
                        "tag_score": 0.0,
                        "hit_sources": ["vector"],
                    }
                )

        results = _filter_and_format(
            candidates,
            cfg,
            project_path,
            tags,
            effective_limit,
            compact,
            recency_weight=effective_recency,
            include_superseded=include_superseded,
            explain=explain,
            min_score=effective_min_score,
        )

        response = {"results": results, "total": len(results), "mode": effective_mode}

        if active_profile:
            response["profile"] = active_profile.name

        if explain:
            scoring_config = {
                "vector_weight": 0.7 if effective_mode == "hybrid" else 1.0,
                "fts_weight": 0.3 if effective_mode == "hybrid" else 0.0,
                "recency_weight": effective_recency,
                "recency_window_days": 90,
                "threshold": 0.2,
            }
            if effective_use_tag_index:
                scoring_config["tag_index_enabled"] = True
                scoring_config["tag_weight"] = effective_tag_weight
            response["scoring_config"] = scoring_config

        return response

    finally:
        # Note: We don't close db here as it's managed by the container
        pass


def _hybrid_search_with_scores(
    db: DatabasePort,
    query_embedding: List[float],
    query_text: str,
    limit: int,
    vector_weight: float = 0.7,
    fts_weight: float = 0.3,
    use_tag_index: bool = False,
    tag_weight: float = 0.3,
) -> List[Dict[str, Any]]:
    """Perform hybrid search and return detailed score breakdown.

    Args:
        db: Database instance.
        query_embedding: Query embedding vector.
        query_text: Original query text for FTS.
        limit: Maximum results.
        vector_weight: Weight for content vector similarity.
        fts_weight: Weight for FTS score.
        use_tag_index: If True, include tag vector similarity in scoring.
        tag_weight: Weight for tag similarity (redistributes from vector_weight).

    Returns list of dicts with:
    - memory: Memory object
    - vec_score: Vector similarity score (0-1)
    - fts_score: Normalized FTS score (0-1)
    - tag_score: Tag similarity score (0-1) if use_tag_index
    - combined_score: Weighted combination
    - hit_sources: List of sources that found this memory
    """
    # Get vector search results
    vec_results = db.search_memories(query_embedding, limit=limit, threshold=0.2)

    # Get FTS results
    fts_results = db.search_fts(query_text, limit=limit)

    # Get tag search results if enabled
    tag_results = []
    if use_tag_index and db.has_tag_index():
        tag_results = db.search_tags(query_embedding, limit=limit)

    # Build score maps
    vec_scores: Dict[str, float] = {}
    vec_memories: Dict[str, Any] = {}
    for memory, distance in vec_results:
        similarity = 1.0 - distance
        vec_scores[memory.id] = similarity
        vec_memories[memory.id] = memory

    # Normalize FTS scores
    fts_scores: Dict[str, float] = {}
    if fts_results:
        min_score = min(score for _, score in fts_results)
        max_score = max(score for _, score in fts_results)
        score_range = max_score - min_score if max_score != min_score else 1.0

        for memory_id, score in fts_results:
            normalized = 1.0 - (score - min_score) / score_range if score_range else 1.0
            fts_scores[memory_id] = normalized

    # Build tag scores map
    tag_scores: Dict[str, float] = {}
    if tag_results:
        for memory_id, distance in tag_results:
            tag_scores[memory_id] = 1.0 - distance

    # Combine results with detailed breakdown
    all_ids = set(vec_scores.keys()) | set(fts_scores.keys()) | set(tag_scores.keys())
    candidates = []

    # Adjust weights if using tag index
    if use_tag_index and tag_results:
        # Redistribute: take tag_weight from vector_weight
        effective_vec_weight = vector_weight * (1.0 - tag_weight)
        effective_tag_weight = vector_weight * tag_weight
        effective_fts_weight = fts_weight
    else:
        effective_vec_weight = vector_weight
        effective_tag_weight = 0.0
        effective_fts_weight = fts_weight

    for memory_id in all_ids:
        vec_score = vec_scores.get(memory_id, 0.0)
        fts_score = fts_scores.get(memory_id, 0.0)
        tag_score = tag_scores.get(memory_id, 0.0)

        # Track hit sources
        hit_sources = []
        if memory_id in vec_scores:
            hit_sources.append("vector")
        if memory_id in fts_scores:
            hit_sources.append("fts")
        if memory_id in tag_scores:
            hit_sources.append("tags")

        # Get memory object
        if memory_id in vec_memories:
            memory = vec_memories[memory_id]
        else:
            memory = db.get_memory(memory_id)
            if not memory:
                continue

        combined_score = (
            (vec_score * effective_vec_weight)
            + (fts_score * effective_fts_weight)
            + (tag_score * effective_tag_weight)
        )

        candidates.append(
            {
                "memory": memory,
                "vec_score": vec_score,
                "fts_score": fts_score,
                "tag_score": tag_score,
                "combined_score": combined_score,
                "hit_sources": hit_sources,
            }
        )

    # Sort by combined score
    candidates.sort(key=lambda x: x["combined_score"], reverse=True)

    return candidates


def _search_fts_only(
    db: DatabasePort,
    cfg: ConfigPort,
    query: str,
    project_path: Optional[str],
    tags: Optional[List[str]],
    limit: int,
    compact: bool,
    warning: Optional[str] = None,
    recency_weight: float = 0.0,
    include_superseded: bool = False,
    explain: bool = False,
    min_score: float = 0.2,
) -> Dict[str, Any]:
    """Perform FTS-only search."""
    fetch_limit = max(50, limit * 5)
    fts_results = db.search_fts(query, limit=fetch_limit)

    if not fts_results:
        result = {"results": [], "total": 0, "mode": "fts"}
        if warning:
            result["warning"] = warning
        if explain:
            result["scoring_config"] = {
                "vector_weight": 0.0,
                "fts_weight": 1.0,
                "recency_weight": recency_weight,
                "recency_window_days": 90,
            }
        return result

    # Normalize FTS scores for explainability
    min_score = min(score for _, score in fts_results)
    max_score = max(score for _, score in fts_results)
    score_range = max_score - min_score if max_score != min_score else 1.0

    # Fetch memories and convert to candidate format
    candidates = []
    for memory_id, score in fts_results:
        memory = db.get_memory(memory_id)
        if memory:
            normalized_fts = (
                1.0 - (score - min_score) / score_range if score_range else 1.0
            )
            candidates.append(
                {
                    "memory": memory,
                    "vec_score": 0.0,
                    "fts_score": normalized_fts,
                    "combined_score": normalized_fts,
                    "hit_sources": ["fts"],
                }
            )

    results = _filter_and_format(
        candidates,
        cfg,
        project_path,
        tags,
        limit,
        compact,
        recency_weight=recency_weight,
        include_superseded=include_superseded,
        explain=explain,
        min_score=min_score,
    )
    result = {"results": results, "total": len(results), "mode": "fts"}
    if warning:
        result["warning"] = warning
    if explain:
        result["scoring_config"] = {
            "vector_weight": 0.0,
            "fts_weight": 1.0,
            "recency_weight": recency_weight,
            "recency_window_days": 90,
        }
    return result


def _filter_and_format(
    candidates: List[Dict[str, Any]],
    cfg: ConfigPort,
    project_path: Optional[str],
    tags: Optional[List[str]],
    limit: int,
    compact: bool,
    recency_weight: float = 0.0,
    include_superseded: bool = False,
    explain: bool = False,
    min_score: float = 0.2,
) -> List[Dict[str, Any]]:
    """Apply post-filtering, recency weighting, and format results.

    Args:
        candidates: List of dicts with memory and score breakdown.
        cfg: Configuration port for accessing settings.
        project_path: Optional project path filter.
        tags: Optional tags filter.
        limit: Maximum results to return.
        compact: Whether to return compact format.
        recency_weight: Weight for recency boost (0.0-1.0).
        include_superseded: Whether to include superseded memories.
        explain: Whether to include detailed scoring breakdown.
        min_score: Minimum score threshold to include in results.

    Returns:
        List of formatted result dictionaries.
    """
    now = time.time()
    # Use config for recency window
    recency_window = cfg.search_recency_window_days * 24 * 3600

    filtered = []

    for candidate in candidates:
        memory = candidate["memory"]
        vec_score = candidate.get("vec_score", 0.0)
        fts_score = candidate.get("fts_score", 0.0)
        tag_score = candidate.get("tag_score", 0.0)
        hit_sources = candidate.get("hit_sources", [])

        # Filter out superseded memories unless explicitly requested
        if not include_superseded:
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

        # Calculate base similarity from combined score
        base_score = candidate.get("combined_score", max(vec_score, fts_score))

        # Calculate recency score (0.0 = old, 1.0 = recent)
        age = now - memory.updated_at
        recency_score = max(0.0, 1.0 - (age / recency_window))

        # Combine similarity and recency
        if recency_weight > 0:
            final_score = (
                1.0 - recency_weight
            ) * base_score + recency_weight * recency_score
        else:
            final_score = base_score

        # Filter by minimum score threshold
        if final_score < min_score:
            continue

        filtered.append(
            {
                "memory": memory,
                "vec_score": vec_score,
                "fts_score": fts_score,
                "tag_score": tag_score,
                "recency_score": recency_score,
                "base_score": base_score,
                "final_score": final_score,
                "hit_sources": hit_sources,
            }
        )

    # Sort by final score (descending)
    filtered.sort(key=lambda x: x["final_score"], reverse=True)

    # Format results
    results = []
    for item in filtered:
        memory = item["memory"]

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
                "score": round(item["final_score"], 3),
                "tokens": _estimate_tokens(memory.content),
            }

            if explain:
                scoring = {
                    "vec_score": round(item["vec_score"], 3),
                    "fts_score": round(item["fts_score"], 3),
                    "recency_score": round(item["recency_score"], 3),
                    "hit_sources": item["hit_sources"],
                }
                if item.get("tag_score", 0.0) > 0:
                    scoring["tag_score"] = round(item["tag_score"], 3)
                result["scoring"] = scoring
        else:
            result = {
                "id": memory.id,
                "content": memory.content,
                "tags": memory.tags,
                "score": round(item["final_score"], 4),
                "project_path": memory.project_path,
                "agent": memory.agent,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
            }

            if explain:
                scoring = {
                    "vec_score": round(item["vec_score"], 4),
                    "fts_score": round(item["fts_score"], 4),
                    "recency_score": round(item["recency_score"], 4),
                    "base_score": round(item["base_score"], 4),
                    "final_score": round(item["final_score"], 4),
                    "hit_sources": item["hit_sources"],
                    "age_days": round((now - memory.updated_at) / 86400, 1),
                }
                if item.get("tag_score", 0.0) > 0:
                    scoring["tag_score"] = round(item["tag_score"], 4)
                result["scoring"] = scoring

        results.append(result)

        if len(results) >= limit:
            break

    return results


def _estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars per token on average)."""
    return len(text) // 4
