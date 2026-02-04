"""Embedding profile management for GMemory.

Supports multiple embedding model configurations with
smooth migration workflow when switching models.
"""

import logging
from typing import Any, Dict, List, Optional

from gmemory.config import config
from gmemory.storage.database import MemoryDatabase

logger = logging.getLogger(__name__)


def list_embedding_profiles() -> Dict[str, Any]:
    """List all available embedding profiles.

    Returns:
        Dict with profiles list and active profile info.
    """
    profiles = config.embedding_profiles
    active = config.embedding_active_profile

    profile_list = []
    for name, settings in profiles.items():
        profile_list.append(
            {
                "name": name,
                "provider": settings.get("provider", "fastembed"),
                "model": settings.get("model", name),
                "dimension": settings.get("dimension", 768),
                "active": name == active,
            }
        )

    # Sort by name, active first
    profile_list.sort(key=lambda p: (not p["active"], p["name"]))

    return {
        "profiles": profile_list,
        "active_profile": active,
        "current_config": {
            "provider": config.embedding_provider,
            "model": config.embedding_model,
            "dimension": config.embedding_dimension,
        },
    }


def get_embedding_profile_detail(name: str) -> Dict[str, Any]:
    """Get detailed information about an embedding profile.

    Args:
        name: Profile name.

    Returns:
        Dict with profile details or error.
    """
    profile = config.get_embedding_profile(name)
    if not profile:
        available = list(config.embedding_profiles.keys())
        return {
            "error": f"Unknown embedding profile: '{name}'",
            "available": available,
        }

    return {
        "name": name,
        "provider": profile.get("provider", "fastembed"),
        "model": profile.get("model", name),
        "dimension": profile.get("dimension", 768),
        "is_active": name == config.embedding_active_profile,
        "description": _get_model_description(profile.get("model", name)),
    }


def _get_model_description(model: str) -> str:
    """Get human-readable description for a model."""
    descriptions = {
        "nomic": "Nomic AI nomic-embed-text-v1.5 - General purpose, 768 dims",
        "bge-small": "BAAI BGE Small - Fast, lightweight, 384 dims",
        "bge-base": "BAAI BGE Base - Balanced quality/speed, 768 dims",
        "all-minilm": "Sentence Transformers MiniLM - Very fast, 384 dims",
    }
    return descriptions.get(model, f"Custom model: {model}")


def check_profile_compatibility(target_profile: str) -> Dict[str, Any]:
    """Check if switching to a profile requires index rebuild.

    Args:
        target_profile: Profile name to switch to.

    Returns:
        Dict with compatibility info and required actions.
    """
    profile = config.get_embedding_profile(target_profile)
    if not profile:
        return {"error": f"Unknown profile: '{target_profile}'"}

    current_dim = config.embedding_dimension
    target_dim = profile.get("dimension", 768)
    current_model = config.embedding_model
    target_model = profile.get("model", target_profile)

    db = MemoryDatabase()
    try:
        # Check current index state
        cursor = db.conn.execute("SELECT COUNT(*) FROM vec_memories")
        vec_count = cursor.fetchone()[0]

        cursor = db.conn.execute("SELECT COUNT(*) FROM memories")
        mem_count = cursor.fetchone()[0]

        # Check tag index
        try:
            cursor = db.conn.execute("SELECT COUNT(*) FROM vec_tags")
            tag_count = cursor.fetchone()[0]
        except Exception:
            tag_count = 0

    finally:
        db.close()

    needs_rebuild = current_dim != target_dim or current_model != target_model

    result = {
        "current_profile": config.embedding_active_profile,
        "target_profile": target_profile,
        "current_dimension": current_dim,
        "target_dimension": target_dim,
        "current_model": current_model,
        "target_model": target_model,
        "dimension_change": current_dim != target_dim,
        "model_change": current_model != target_model,
        "needs_rebuild": needs_rebuild,
        "memories_to_reindex": mem_count if needs_rebuild else 0,
        "vectors_affected": vec_count,
        "tag_vectors_affected": tag_count,
    }

    if needs_rebuild:
        result["required_actions"] = [
            '1. Update config.toml: [embedding.active_profile] = "{}"'.format(
                target_profile
            ),
            "2. Run: gmemory reindex --target=embeddings --apply",
            "3. Run: gmemory reindex --target=tags --apply (if using tag index)",
            "4. Run: gmemory compact (optional, reclaim space)",
        ]
        result["warning"] = (
            f"Switching from {current_model} ({current_dim}d) to {target_model} ({target_dim}d) "
            f"requires rebuilding {mem_count} embeddings. This may take several minutes."
        )
    else:
        result["message"] = "No rebuild required. Profiles are compatible."

    return result


def switch_embedding_profile(
    target_profile: str,
    rebuild: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Switch to a different embedding profile.

    Args:
        target_profile: Profile name to switch to.
        rebuild: If True, automatically rebuild indexes.
        dry_run: If True, only show what would happen.

    Returns:
        Dict with switch results.
    """
    # Check compatibility first
    compat = check_profile_compatibility(target_profile)
    if "error" in compat:
        return compat

    if dry_run:
        compat["dry_run"] = True
        compat["message"] = (
            "Dry run - no changes made. "
            "Use --apply to switch profile and rebuild indexes."
        )
        return compat

    # Actually switch profile (runtime only)
    if not config.set_embedding_profile(target_profile):
        return {"error": f"Failed to set profile: {target_profile}"}

    result = {
        "success": True,
        "switched_to": target_profile,
        "new_config": {
            "provider": config.embedding_provider,
            "model": config.embedding_model,
            "dimension": config.embedding_dimension,
        },
    }

    # Rebuild if requested and needed
    if rebuild and compat.get("needs_rebuild"):
        from gmemory.commands.lifecycle import reindex_all

        rebuild_result = reindex_all(dry_run=False, target="all")
        result["rebuild"] = rebuild_result

        if not rebuild_result.get("success", False):
            result["warning"] = (
                "Profile switched but rebuild had errors. Check rebuild results."
            )

    result["note"] = (
        "Profile switched for this session. "
        'To persist, update config.toml: [embedding.active_profile] = "{}"'.format(
            target_profile
        )
    )

    return result


def get_index_version_info() -> Dict[str, Any]:
    """Get version information about current indexes.

    Useful for tracking which model was used to create embeddings.

    Returns:
        Dict with index version info.
    """
    db = MemoryDatabase()
    try:
        # Get memory stats
        cursor = db.conn.execute("SELECT COUNT(*) FROM memories")
        mem_count = cursor.fetchone()[0]

        cursor = db.conn.execute("SELECT COUNT(*) FROM vec_memories")
        vec_count = cursor.fetchone()[0]

        cursor = db.conn.execute("SELECT COUNT(*) FROM memories_fts")
        fts_count = cursor.fetchone()[0]

        try:
            cursor = db.conn.execute("SELECT COUNT(*) FROM vec_tags")
            tag_count = cursor.fetchone()[0]
        except Exception:
            tag_count = 0

        # Get oldest and newest memory timestamps
        cursor = db.conn.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM memories"
        )
        row = cursor.fetchone()
        oldest = row[0] if row else None
        newest = row[1] if row else None

        return {
            "current_config": {
                "provider": config.embedding_provider,
                "model": config.embedding_model,
                "dimension": config.embedding_dimension,
                "active_profile": config.embedding_active_profile,
            },
            "index_stats": {
                "total_memories": mem_count,
                "vector_embeddings": vec_count,
                "fts_entries": fts_count,
                "tag_embeddings": tag_count,
                "vectors_missing": mem_count - vec_count,
                "fts_missing": mem_count - fts_count,
            },
            "coverage": {
                "vector_coverage": round(vec_count / mem_count * 100, 1)
                if mem_count > 0
                else 0,
                "fts_coverage": round(fts_count / mem_count * 100, 1)
                if mem_count > 0
                else 0,
                "tag_coverage": round(tag_count / mem_count * 100, 1)
                if mem_count > 0
                else 0,
            },
            "time_range": {
                "oldest_memory": oldest,
                "newest_memory": newest,
            },
        }

    finally:
        db.close()
