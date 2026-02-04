"""Rebuild command for GMemory.

Re-embeds all memories when embedding model changes or vectors become corrupted.
"""

import logging
from typing import Dict, Any

from gmemory.storage.database import MemoryDatabase
from gmemory.storage.embedder import get_embedder, NoOpEmbedder, is_valid_embedding
from gmemory.config import config

logger = logging.getLogger(__name__)


def rebuild_embeddings(
    dry_run: bool = False,
    batch_size: int = 50,
) -> Dict[str, Any]:
    """Rebuild all memory embeddings.

    Use this when:
    - Switching to a different embedding model
    - Embedding dimension changes
    - Vector index becomes corrupted
    - Upgrading from NoOp to real embeddings

    Args:
        dry_run: If True, only report what would be done without making changes.
        batch_size: Number of memories to process at a time.

    Returns:
        Dict with rebuild statistics.
    """
    # Get embedder
    try:
        embedder = get_embedder()
        if isinstance(embedder, NoOpEmbedder):
            return {
                "success": False,
                "error": "Cannot rebuild with NoOpEmbedder. Configure a real embedding provider.",
            }
    except Exception as e:
        return {"success": False, "error": f"Failed to initialize embedder: {e}"}

    db = MemoryDatabase(embedding_dimension=embedder.dimension)
    try:
        # Get all memory IDs
        cursor = db.conn.execute("SELECT id, content FROM memories")
        memories = cursor.fetchall()
        total = len(memories)

        if total == 0:
            return {
                "success": True,
                "total": 0,
                "rebuilt": 0,
                "skipped": 0,
                "failed": 0,
                "message": "No memories to rebuild.",
            }

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "total": total,
                "message": f"Would rebuild {total} memory embeddings.",
                "model": config.embedding_model,
                "dimension": embedder.dimension,
            }

        # Process in batches
        rebuilt = 0
        skipped = 0
        failed = 0

        for i in range(0, total, batch_size):
            batch = memories[i : i + batch_size]
            texts = [row["content"] for row in batch]
            ids = [row["id"] for row in batch]

            try:
                # Batch embed
                embeddings = embedder.embed_batch(texts)

                # Update each memory's vector
                for memory_id, embedding in zip(ids, embeddings):
                    if is_valid_embedding(embedding, embedder.dimension):
                        embedding_blob = db._serialize_float32(embedding)
                        db.conn.execute(
                            """
                            INSERT OR REPLACE INTO vec_memories (memory_id, embedding)
                            VALUES (?, ?)
                            """,
                            (memory_id, embedding_blob),
                        )
                        rebuilt += 1
                    else:
                        logger.warning(f"Invalid embedding for memory {memory_id}")
                        failed += 1

                db.conn.commit()
                logger.info(f"Rebuilt {rebuilt}/{total} embeddings...")

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                failed += len(batch)

        return {
            "success": True,
            "total": total,
            "rebuilt": rebuilt,
            "skipped": skipped,
            "failed": failed,
            "model": config.embedding_model,
            "dimension": embedder.dimension,
        }

    finally:
        db.close()


def rebuild_fts_index() -> Dict[str, Any]:
    """Rebuild the FTS5 full-text search index.

    Use this when:
    - FTS index becomes corrupted
    - Upgrading from a version without FTS

    Returns:
        Dict with rebuild statistics.
    """
    db = MemoryDatabase()
    try:
        # Clear existing FTS data
        db.conn.execute("DELETE FROM memories_fts")

        # Rebuild from memories table
        cursor = db.conn.execute("SELECT id, content, tags FROM memories")
        memories = cursor.fetchall()
        total = len(memories)

        if total == 0:
            return {
                "success": True,
                "total": 0,
                "message": "No memories to index.",
            }

        # Insert all memories into FTS
        for row in memories:
            db.conn.execute(
                """
                INSERT INTO memories_fts (memory_id, content, tags)
                VALUES (?, ?, ?)
                """,
                (row["id"], row["content"], row["tags"]),
            )

        db.conn.commit()

        return {
            "success": True,
            "total": total,
            "indexed": total,
            "message": f"Rebuilt FTS index for {total} memories.",
        }

    except Exception as e:
        return {"success": False, "error": f"FTS rebuild failed: {e}"}

    finally:
        db.close()
