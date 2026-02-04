"""Data lifecycle management commands for GMemory.

Provides purge, compact, reindex, and archive functionality for
long-term database maintenance without background services.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from gmemory.config import config
from gmemory.storage.database import MemoryDatabase

logger = logging.getLogger(__name__)


def purge_old_memories(
    days: Optional[int] = None,
    dry_run: bool = True,
    archive: Optional[bool] = None,
    archive_path: Optional[str] = None,
    project_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Purge memories older than specified days.

    Args:
        days: Delete memories older than this many days.
              If None, uses config.lifecycle_retention_days.
              If 0, no purge is performed.
        dry_run: If True (default), only report what would be deleted.
        archive: If True, export memories before deletion.
                 If None, uses config.lifecycle_archive_before_purge.
        archive_path: Path for archive file. Auto-generated if not provided.
        project_path: Optional filter to only purge from specific project.

    Returns:
        Dict with purge statistics and archived file path if applicable.
    """
    # Resolve config defaults
    retention_days = days if days is not None else config.lifecycle_retention_days
    should_archive = (
        archive if archive is not None else config.lifecycle_archive_before_purge
    )

    if retention_days <= 0:
        return {
            "success": True,
            "purged": 0,
            "message": "Retention days is 0 or negative. No purge performed.",
        }

    cutoff_timestamp = time.time() - (retention_days * 24 * 3600)
    cutoff_date = datetime.fromtimestamp(cutoff_timestamp).isoformat()

    db = MemoryDatabase()
    try:
        # Build query for memories to purge
        query = "SELECT id, content, tags, created_at, updated_at, project_path FROM memories WHERE updated_at < ?"
        params: List[Any] = [cutoff_timestamp]

        if project_path:
            query += " AND project_path = ?"
            params.append(project_path)

        # Don't purge superseded memories that are still referenced
        query += " AND id NOT IN (SELECT superseded_by FROM memories WHERE superseded_by IS NOT NULL)"

        cursor = db.conn.execute(query, params)
        memories_to_purge = cursor.fetchall()
        total = len(memories_to_purge)

        if total == 0:
            return {
                "success": True,
                "purged": 0,
                "cutoff_date": cutoff_date,
                "message": f"No memories older than {retention_days} days found.",
            }

        if dry_run:
            # Group by project for summary
            by_project: Dict[str, int] = {}
            for row in memories_to_purge:
                proj = row["project_path"] or "(no project)"
                by_project[proj] = by_project.get(proj, 0) + 1

            return {
                "success": True,
                "dry_run": True,
                "would_purge": total,
                "cutoff_date": cutoff_date,
                "retention_days": retention_days,
                "by_project": by_project,
                "message": f"Would purge {total} memories older than {retention_days} days.",
            }

        # Archive if requested
        archived_path = None
        if should_archive and total > 0:
            if archive_path:
                archived_path = archive_path
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archived_path = str(
                    Path.home() / ".gmemory" / f"archive_{timestamp}.json"
                )

            # Export memories to archive
            archive_data = {
                "archived_at": datetime.now().isoformat(),
                "cutoff_date": cutoff_date,
                "retention_days": retention_days,
                "total": total,
                "memories": [],
            }

            for row in memories_to_purge:
                archive_data["memories"].append(
                    {
                        "id": row["id"],
                        "content": row["content"],
                        "tags": row["tags"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "project_path": row["project_path"],
                    }
                )

            # Write archive file
            Path(archived_path).parent.mkdir(parents=True, exist_ok=True)
            with open(archived_path, "w", encoding="utf-8") as f:
                json.dump(archive_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Archived {total} memories to {archived_path}")

        # Perform deletion
        memory_ids = [row["id"] for row in memories_to_purge]

        # Delete from vec_memories
        db.conn.executemany(
            "DELETE FROM vec_memories WHERE memory_id = ?",
            [(mid,) for mid in memory_ids],
        )

        # Delete from vec_tags
        try:
            db.conn.executemany(
                "DELETE FROM vec_tags WHERE memory_id = ?",
                [(mid,) for mid in memory_ids],
            )
        except Exception:
            pass  # vec_tags may not exist

        # Delete from memories_fts
        db.conn.executemany(
            "DELETE FROM memories_fts WHERE memory_id = ?",
            [(mid,) for mid in memory_ids],
        )

        # Delete from memories
        db.conn.executemany(
            "DELETE FROM memories WHERE id = ?", [(mid,) for mid in memory_ids]
        )

        db.conn.commit()

        result = {
            "success": True,
            "purged": total,
            "cutoff_date": cutoff_date,
            "retention_days": retention_days,
            "message": f"Purged {total} memories older than {retention_days} days.",
        }

        if archived_path:
            result["archived_to"] = archived_path

        return result

    except Exception as e:
        logger.error(f"Purge failed: {e}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()


def compact_database(
    vacuum: bool = True,
    analyze: bool = True,
    rebuild_fts: bool = False,
) -> Dict[str, Any]:
    """Compact and optimize the database.

    Args:
        vacuum: If True, run VACUUM to reclaim space.
        analyze: If True, run ANALYZE to update query planner statistics.
        rebuild_fts: If True, rebuild FTS index (can fix corruption).

    Returns:
        Dict with compaction statistics.
    """
    db = MemoryDatabase()
    try:
        results: Dict[str, Any] = {"success": True, "operations": []}

        # Get initial size
        db_path = config.db_path
        initial_size = db_path.stat().st_size if db_path.exists() else 0

        # Run ANALYZE first (updates statistics)
        if analyze:
            db.conn.execute("ANALYZE")
            results["operations"].append("ANALYZE")
            logger.info("Ran ANALYZE to update query statistics")

        # Rebuild FTS if requested
        if rebuild_fts:
            try:
                db.conn.execute(
                    "INSERT INTO memories_fts(memories_fts) VALUES('rebuild')"
                )
                results["operations"].append("FTS rebuild")
                logger.info("Rebuilt FTS index")
            except Exception as e:
                logger.warning(f"FTS rebuild failed: {e}")
                results["fts_rebuild_error"] = str(e)

        # Run VACUUM (must be outside transaction)
        if vacuum:
            db.conn.execute("VACUUM")
            results["operations"].append("VACUUM")
            logger.info("Ran VACUUM to reclaim space")

        # Get final size
        final_size = db_path.stat().st_size if db_path.exists() else 0
        space_saved = initial_size - final_size

        results["initial_size_bytes"] = initial_size
        results["final_size_bytes"] = final_size
        results["space_saved_bytes"] = space_saved
        results["space_saved_mb"] = round(space_saved / (1024 * 1024), 2)
        results["message"] = (
            f"Compaction complete. Saved {results['space_saved_mb']} MB."
        )

        return results

    except Exception as e:
        logger.error(f"Compact failed: {e}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()


def reindex_all(
    dry_run: bool = True,
    target: str = "all",
) -> Dict[str, Any]:
    """Rebuild all indexes (embeddings, FTS, tags).

    Args:
        dry_run: If True (default), only report what would be done.
        target: What to reindex - "all", "embeddings", "fts", "tags".

    Returns:
        Dict with reindex statistics.
    """
    from gmemory.commands.rebuild import rebuild_embeddings, rebuild_fts_index

    results: Dict[str, Any] = {"success": True, "targets": []}

    if target in ("all", "embeddings"):
        emb_result = rebuild_embeddings(dry_run=dry_run)
        results["embeddings"] = emb_result
        results["targets"].append("embeddings")
        if not emb_result.get("success", False) and not dry_run:
            results["success"] = False

    if target in ("all", "fts"):
        if dry_run:
            db = MemoryDatabase()
            try:
                cursor = db.conn.execute("SELECT COUNT(*) FROM memories")
                count = cursor.fetchone()[0]
                results["fts"] = {
                    "success": True,
                    "dry_run": True,
                    "total": count,
                    "message": f"Would rebuild FTS index for {count} memories.",
                }
            finally:
                db.close()
        else:
            fts_result = rebuild_fts_index()
            results["fts"] = fts_result
        results["targets"].append("fts")

    if target in ("all", "tags"):
        results["tags"] = _rebuild_tag_index(dry_run=dry_run)
        results["targets"].append("tags")

    return results


def _rebuild_tag_index(dry_run: bool = True) -> Dict[str, Any]:
    """Rebuild the tag vector index.

    Args:
        dry_run: If True, only report what would be done.

    Returns:
        Dict with rebuild statistics.
    """
    from gmemory.storage.embedder import get_embedder, NoOpEmbedder

    try:
        embedder = get_embedder()
        if isinstance(embedder, NoOpEmbedder):
            return {
                "success": False,
                "error": "Cannot rebuild tag index with NoOpEmbedder.",
            }
    except Exception as e:
        return {"success": False, "error": f"Failed to initialize embedder: {e}"}

    db = MemoryDatabase(embedding_dimension=embedder.dimension)
    try:
        # Get all memories with tags
        cursor = db.conn.execute(
            "SELECT id, tags FROM memories WHERE tags IS NOT NULL AND tags != ''"
        )
        memories = cursor.fetchall()
        total = len(memories)

        if total == 0:
            return {
                "success": True,
                "total": 0,
                "message": "No memories with tags to index.",
            }

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "total": total,
                "message": f"Would rebuild tag index for {total} memories.",
            }

        # Clear existing tag index
        try:
            db.conn.execute("DELETE FROM vec_tags")
        except Exception:
            pass  # Table may not exist

        # Rebuild tag embeddings
        rebuilt = 0
        failed = 0
        batch_size = 50

        for i in range(0, total, batch_size):
            batch = memories[i : i + batch_size]
            tags_list = [row["tags"] for row in batch]
            ids = [row["id"] for row in batch]

            try:
                embeddings = embedder.embed_batch(tags_list)
                for memory_id, embedding in zip(ids, embeddings):
                    db._store_tag_embedding(memory_id, embedding)
                    rebuilt += 1
                db.conn.commit()
            except Exception as e:
                logger.error(f"Tag embedding batch failed: {e}")
                failed += len(batch)

        return {
            "success": True,
            "total": total,
            "rebuilt": rebuilt,
            "failed": failed,
            "message": f"Rebuilt tag index for {rebuilt} memories.",
        }

    finally:
        db.close()


def get_lifecycle_stats() -> Dict[str, Any]:
    """Get statistics relevant to lifecycle management.

    Returns:
        Dict with memory age distribution, size info, etc.
    """
    db = MemoryDatabase()
    try:
        now = time.time()
        day_seconds = 24 * 3600

        # Age distribution
        age_buckets = {
            "last_7_days": 0,
            "last_30_days": 0,
            "last_90_days": 0,
            "older_than_90_days": 0,
        }

        cursor = db.conn.execute("SELECT updated_at FROM memories")
        for row in cursor:
            age_days = (now - row["updated_at"]) / day_seconds
            if age_days <= 7:
                age_buckets["last_7_days"] += 1
            elif age_days <= 30:
                age_buckets["last_30_days"] += 1
            elif age_days <= 90:
                age_buckets["last_90_days"] += 1
            else:
                age_buckets["older_than_90_days"] += 1

        # Total counts
        cursor = db.conn.execute("SELECT COUNT(*) FROM memories")
        total_memories = cursor.fetchone()[0]

        cursor = db.conn.execute("SELECT COUNT(*) FROM vec_memories")
        total_vectors = cursor.fetchone()[0]

        cursor = db.conn.execute("SELECT COUNT(*) FROM memories_fts")
        total_fts = cursor.fetchone()[0]

        # Tag index count
        try:
            cursor = db.conn.execute("SELECT COUNT(*) FROM vec_tags")
            total_tags = cursor.fetchone()[0]
        except Exception:
            total_tags = 0

        # Database size
        db_path = config.db_path
        db_size = db_path.stat().st_size if db_path.exists() else 0

        # Superseded count
        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE superseded_by IS NOT NULL"
        )
        superseded_count = cursor.fetchone()[0]

        return {
            "total_memories": total_memories,
            "total_vectors": total_vectors,
            "total_fts_entries": total_fts,
            "total_tag_vectors": total_tags,
            "superseded_count": superseded_count,
            "age_distribution": age_buckets,
            "database_size_bytes": db_size,
            "database_size_mb": round(db_size / (1024 * 1024), 2),
            "retention_days_config": config.lifecycle_retention_days,
            "auto_compact_threshold": config.lifecycle_auto_compact_threshold,
        }

    finally:
        db.close()
