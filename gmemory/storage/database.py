import sqlite3
import struct
import json
import time
import logging
from typing import List, Optional, Tuple, Any, Dict
from pathlib import Path
import uuid
import sqlite_vec

from gmemory.config import config
from gmemory.models import Memory, ProcessedSession
from gmemory.validation import validate_memory
from gmemory.storage.migrations import apply_migrations, get_migration_status

logger = logging.getLogger(__name__)

# Schema version for migration tracking
SCHEMA_VERSION = 6


class MemoryDatabase:
    """
    SQLite-based storage for memories using sqlite-vec for vector search.
    """

    def __init__(self, embedding_dimension: Optional[int] = None):
        """Initialize database.

        Args:
            embedding_dimension: Override embedding dimension. If None, uses config value.
                                 Pass embedder.dimension for consistency.
        """
        self.db_path = config.db_path
        self._embedding_dim = embedding_dimension or config.embedding_dimension
        self._vec_loaded = False
        self._vec_load_error: Optional[str] = None
        self._ensure_db_dir()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Load sqlite-vec extension with diagnostic logging
        self._load_sqlite_vec()

        self._configure_pragma()
        self._init_tables()
        self._run_migrations()
        self._validate_vector_dimension()
        self._log_diagnostics()

    def _load_sqlite_vec(self) -> None:
        """Load sqlite-vec extension with diagnostic logging."""
        try:
            self.conn.enable_load_extension(True)
            sqlite_vec.load(self.conn)
            self.conn.enable_load_extension(False)
            self._vec_loaded = True
            logger.debug("sqlite-vec extension loaded successfully")
        except Exception as e:
            self._vec_loaded = False
            self._vec_load_error = str(e)
            logger.error(
                f"[GMEM-DB-201] Failed to load sqlite-vec extension: {e}. "
                f"Vector search will be unavailable. "
                f"Ensure sqlite-vec is installed: pip install sqlite-vec"
            )

    def _log_diagnostics(self) -> None:
        """Log diagnostic information about database state."""
        diag = self.get_diagnostics()

        if not diag["vec_extension_loaded"]:
            logger.warning(
                f"[GMEM-DB-201] sqlite-vec not loaded: {diag['vec_load_error']}. "
                f"Vector search disabled. Install with: pip install sqlite-vec"
            )

        if diag["vec_dimension_mismatch"]:
            logger.warning(
                f"[GMEM-DB-204] Vector dimension mismatch detected. "
                f"Expected: {diag['expected_dimension']}, "
                f"Run 'gmemory rebuild --target=embeddings' to fix."
            )

        if diag["pending_migrations"] > 0:
            logger.info(
                f"Database has {diag['pending_migrations']} pending migration(s). "
                f"Current version: {diag['schema_version']}"
            )

    def _run_migrations(self) -> None:
        """Run any pending database migrations."""
        try:
            applied = apply_migrations(self.conn)
            if applied:
                logger.info(f"Applied {len(applied)} migration(s): {applied}")
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

    def _ensure_db_dir(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _configure_pragma(self):
        """Configure SQLite for better performance."""
        self.conn.execute("PRAGMA busy_timeout = 5000;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def _init_tables(self):
        """Initialize database tables."""
        with self.conn:
            # Main memories table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    tags TEXT,
                    importance TEXT,
                    memory_type TEXT,
                    agent TEXT,
                    source_session_id TEXT,
                    project_path TEXT,
                    project_name TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
            """)

            # Vector table for semantic search
            dim = self._embedding_dim
            self.conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories USING vec0(
                    memory_id TEXT PRIMARY KEY,
                    embedding float32[{dim}] distance_metric=cosine
                );
            """)

            # FTS5 full-text search index (content-based)
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    memory_id,
                    content,
                    tags,
                    tokenize='porter unicode61'
                );
            """)

            # Sync existing memories to FTS if needed
            self._sync_fts_index()

            # Processed sessions tracking
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_sessions (
                    session_id TEXT,
                    agent TEXT,
                    processed_at INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'processed',
                    reason TEXT,
                    PRIMARY KEY (agent, session_id)
                );
            """)

    def _validate_vector_dimension(self):
        """Validate that vector table dimension matches expected dimension.

        Logs a warning if there's a mismatch, which can cause search failures.
        """
        try:
            # Check if vec_memories has any data
            cursor = self.conn.execute("SELECT COUNT(*) FROM vec_memories")
            count = cursor.fetchone()[0]
            if count == 0:
                return  # Empty table, no validation needed

            # Try to query with a test vector of expected dimension
            test_vector = [0.0] * self._embedding_dim
            test_blob = self._serialize_float32(test_vector)

            # This will fail if dimensions don't match
            self.conn.execute(
                "SELECT memory_id FROM vec_memories WHERE embedding MATCH ? AND k = 1",
                (test_blob,),
            ).fetchone()

        except sqlite3.OperationalError as e:
            error_msg = str(e)
            if "dimension" in error_msg.lower() or "vector" in error_msg.lower():
                logger.warning(
                    f"Vector dimension mismatch detected. Expected {self._embedding_dim} dims. "
                    f"Existing vectors may have different dimensions. "
                    f"Consider rebuilding vec_memories table or re-embedding all memories. "
                    f"Error: {e}"
                )
            else:
                logger.warning(f"Vector validation error: {e}")

    def _sync_fts_index(self):
        """Sync memories table to FTS5 index for full-text search.

        Only inserts memories that are not already in the FTS index.
        """
        try:
            # Count existing FTS entries
            cursor = self.conn.execute("SELECT COUNT(*) FROM memories_fts")
            fts_count = cursor.fetchone()[0]

            cursor = self.conn.execute("SELECT COUNT(*) FROM memories")
            mem_count = cursor.fetchone()[0]

            if fts_count >= mem_count:
                return  # FTS is up to date

            # Insert missing entries
            with self.conn:
                self.conn.execute("""
                    INSERT INTO memories_fts (memory_id, content, tags)
                    SELECT id, content, tags FROM memories
                    WHERE id NOT IN (SELECT memory_id FROM memories_fts)
                """)
                inserted = self.conn.total_changes
                if inserted > 0:
                    logger.info(f"Synced {inserted} memories to FTS index")

        except sqlite3.OperationalError as e:
            logger.warning(f"FTS sync error: {e}")

    def _serialize_float32(self, vector: List[float]) -> bytes:
        """Serialize a list of floats into a binary blob for sqlite-vec."""
        return struct.pack(f"{len(vector)}f", *vector)

    def _store_tag_embedding(self, memory_id: str, tag_embedding: List[float]) -> None:
        """Store tag embedding in the vec_tags table (dual index).

        Args:
            memory_id: The memory ID to associate with.
            tag_embedding: The embedding vector for the memory's tags.
        """
        try:
            embedding_blob = self._serialize_float32(tag_embedding)
            self.conn.execute(
                """
                INSERT OR REPLACE INTO vec_tags (memory_id, embedding)
                VALUES (?, ?)
                """,
                (memory_id, embedding_blob),
            )
        except sqlite3.OperationalError as e:
            # vec_tags table may not exist if migration hasn't run
            logger.debug(f"Could not store tag embedding: {e}")

    def _has_tag_index(self) -> bool:
        """Check if the vec_tags table exists and has data (internal)."""
        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM vec_tags")
            return cursor.fetchone()[0] > 0
        except sqlite3.OperationalError:
            return False

    def has_tag_index(self) -> bool:
        """Check if the tag index exists and has data.

        Public interface method for DatabasePort protocol.
        """
        return self._has_tag_index()

    def search_tags(
        self, tag_embedding: List[float], limit: int = 50
    ) -> List[Tuple[str, float]]:
        """Search for memories by tag similarity.

        Args:
            tag_embedding: Embedding vector for the query tags.
            limit: Maximum number of results.

        Returns:
            List of (memory_id, distance) tuples.
        """
        try:
            embedding_blob = self._serialize_float32(tag_embedding)
            cursor = self.conn.execute(
                """
                SELECT memory_id, distance
                FROM vec_tags
                WHERE embedding MATCH ? AND k = ?
                ORDER BY distance
                """,
                (embedding_blob, limit),
            )
            return [(row[0], row[1]) for row in cursor]
        except sqlite3.OperationalError as e:
            logger.debug(f"Tag search unavailable: {e}")
            return []

    def add_memory(
        self,
        memory: Memory,
        embedding: Optional[List[float]] = None,
        tag_embedding: Optional[List[float]] = None,
        validate: bool = True,
    ):
        """Add a memory and its embedding to the database.

        Args:
            memory: Memory object to add.
            embedding: Optional content embedding vector.
            tag_embedding: Optional tag embedding vector (for dual index).
            validate: If True, validate memory fields before insert.

        Raises:
            ValidationError: If validate=True and validation fails.
        """
        if validate:
            validate_memory(
                memory_id=memory.id,
                content=memory.content,
                tags=memory.tags,
                importance=memory.importance,
                memory_type=memory.memory_type,
                created_at=memory.created_at,
                updated_at=memory.updated_at,
                strict=True,
            )

        tags_json = json.dumps(memory.tags)

        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO memories (
                    id, content, tags, importance, memory_type, agent, 
                    source_session_id, project_path, project_name, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    memory.id,
                    memory.content,
                    tags_json,
                    memory.importance,
                    memory.memory_type,
                    memory.agent,
                    memory.source_session_id,
                    memory.project_path,
                    memory.project_name,
                    memory.created_at,
                    memory.updated_at,
                ),
            )

            if embedding:
                embedding_blob = self._serialize_float32(embedding)
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO vec_memories (memory_id, embedding)
                    VALUES (?, ?)
                """,
                    (memory.id, embedding_blob),
                )

            # Store tag embedding if provided (dual index)
            if tag_embedding:
                self._store_tag_embedding(memory.id, tag_embedding)

            # Update FTS index
            self.conn.execute(
                "DELETE FROM memories_fts WHERE memory_id = ?", (memory.id,)
            )
            self.conn.execute(
                """
                INSERT INTO memories_fts (memory_id, content, tags)
                VALUES (?, ?, ?)
            """,
                (memory.id, memory.content, tags_json),
            )

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by ID."""
        cursor = self.conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if row:
            return Memory.from_dict(dict(row))
        return None

    def update_memory(
        self,
        memory: Memory,
        embedding: Optional[List[float]] = None,
        tag_embedding: Optional[List[float]] = None,
        validate: bool = True,
    ):
        """Update an existing memory.

        Args:
            memory: Memory object with updated fields.
            embedding: Optional new content embedding vector.
            tag_embedding: Optional new tag embedding vector (for dual index).
            validate: If True, validate memory fields before update.

        Raises:
            ValidationError: If validate=True and validation fails.
        """
        if validate:
            validate_memory(
                memory_id=memory.id,
                content=memory.content,
                tags=memory.tags,
                importance=memory.importance,
                memory_type=memory.memory_type,
                strict=True,
            )

        tags_json = json.dumps(memory.tags)

        with self.conn:
            self.conn.execute(
                """
                UPDATE memories SET
                    content = ?, tags = ?, importance = ?, memory_type = ?,
                    agent = ?, source_session_id = ?, project_path = ?, 
                    project_name = ?, updated_at = ?
                WHERE id = ?
            """,
                (
                    memory.content,
                    tags_json,
                    memory.importance,
                    memory.memory_type,
                    memory.agent,
                    memory.source_session_id,
                    memory.project_path,
                    memory.project_name,
                    int(time.time()),
                    memory.id,
                ),
            )

            if embedding:
                embedding_blob = self._serialize_float32(embedding)
                self.conn.execute(
                    """
                    UPDATE vec_memories SET embedding = ? WHERE memory_id = ?
                """,
                    (embedding_blob, memory.id),
                )

            # Update tag embedding if provided (dual index)
            if tag_embedding:
                self._store_tag_embedding(memory.id, tag_embedding)

            # Update FTS index
            self.conn.execute(
                "DELETE FROM memories_fts WHERE memory_id = ?", (memory.id,)
            )
            self.conn.execute(
                """
                INSERT INTO memories_fts (memory_id, content, tags)
                VALUES (?, ?, ?)
            """,
                (memory.id, memory.content, tags_json),
            )

    def delete_memory(self, memory_id: str):
        """Delete a memory."""
        with self.conn:
            self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self.conn.execute(
                "DELETE FROM vec_memories WHERE memory_id = ?", (memory_id,)
            )
            self.conn.execute(
                "DELETE FROM memories_fts WHERE memory_id = ?", (memory_id,)
            )
            # Also delete from tag index if it exists
            try:
                self.conn.execute(
                    "DELETE FROM vec_tags WHERE memory_id = ?", (memory_id,)
                )
            except sqlite3.OperationalError:
                pass  # vec_tags table may not exist

    def supersede_memory(
        self,
        old_memory_id: str,
        new_memory: Memory,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """Mark an old memory as superseded and add a new replacement memory.

        This is the recommended way to update/replace memories while preserving
        history. The old memory is marked with superseded_by pointing to the
        new memory's ID, and the new memory is added.

        Args:
            old_memory_id: ID of the memory to supersede.
            new_memory: The new memory that replaces the old one.
            embedding: Optional embedding for the new memory.

        Returns:
            True if successful, False if old memory not found.
        """
        old_memory = self.get_memory(old_memory_id)
        if not old_memory:
            return False

        with self.conn:
            # Mark old memory as superseded
            self.conn.execute(
                "UPDATE memories SET superseded_by = ?, updated_at = ? WHERE id = ?",
                (new_memory.id, int(time.time()), old_memory_id),
            )

            # Add the new memory
            self.add_memory(new_memory, embedding, validate=True)

        return True

    def get_active_memories(
        self,
        limit: int = 100,
        offset: int = 0,
        project_path: Optional[str] = None,
    ) -> List[Memory]:
        """Get memories that have not been superseded.

        Args:
            limit: Maximum number of memories to return.
            offset: Number of memories to skip (for pagination).
            project_path: Optional filter by project path.

        Returns:
            List of active (non-superseded) memories.
        """
        if project_path:
            cursor = self.conn.execute(
                """
                SELECT * FROM memories 
                WHERE superseded_by IS NULL AND project_path = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (project_path, limit, offset),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT * FROM memories 
                WHERE superseded_by IS NULL
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )

        return [Memory.from_dict(dict(row)) for row in cursor]

    def search_memories(
        self, query_embedding: List[float], limit: int = 10, threshold: float = 0.5
    ) -> List[Tuple[Memory, float]]:
        """Search for similar memories."""
        # Note: sqlite-vec uses cosine distance (lower is better, 0 is identical)
        # If we want similarity (higher is better), we might need to interpret the distance.
        # But here let's assume we return distance.

        embedding_blob = self._serialize_float32(query_embedding)

        cursor = self.conn.execute(
            """
            SELECT m.*, v.distance
            FROM vec_memories v
            JOIN memories m ON v.memory_id = m.id
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY v.distance
        """,
            (embedding_blob, limit),
        )

        results = []
        for row in cursor:
            distance = row["distance"]
            # Simple threshold check (cosine distance ranges from 0 to 2)
            # If threshold is similarity (0-1), this logic needs adjustment.
            # Assuming threshold is max distance here.
            # However, typically people use similarity. Cosine Similarity = 1 - Cosine Distance.
            # If the user expects similarity threshold (e.g. > 0.7),
            # then distance must be < (1 - 0.7) = 0.3.

            # Let's interpret threshold as minimum similarity.
            similarity = 1.0 - distance
            if similarity >= threshold:
                memory = Memory.from_dict(
                    {k: row[k] for k in row.keys() if k != "distance"}
                )
                results.append((memory, distance))

        return results

    def search_fts(self, query: str, limit: int = 50) -> List[Tuple[str, float]]:
        """Full-text search using FTS5.

        Args:
            query: Search query (supports FTS5 syntax like AND, OR, NOT, "phrase").
            limit: Maximum number of results.

        Returns:
            List of (memory_id, bm25_score) tuples, sorted by relevance.
        """
        try:
            # Escape special FTS5 characters and build query
            # For simple queries, wrap in quotes for phrase matching
            safe_query = query.replace('"', '""')

            cursor = self.conn.execute(
                """
                SELECT memory_id, bm25(memories_fts) as score
                FROM memories_fts
                WHERE memories_fts MATCH ?
                ORDER BY score
                LIMIT ?
            """,
                (f'"{safe_query}" OR {safe_query}', limit),
            )

            return [(row["memory_id"], row["score"]) for row in cursor]

        except sqlite3.OperationalError as e:
            logger.warning(f"FTS search error: {e}")
            return []

    def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        limit: int = 10,
        vector_weight: float = 0.7,
        fts_weight: float = 0.3,
        threshold: float = 0.3,
    ) -> List[Tuple[Memory, float]]:
        """Hybrid search combining vector similarity and full-text search.

        Args:
            query_embedding: Vector embedding of the query.
            query_text: Original query text for FTS.
            limit: Maximum number of results.
            vector_weight: Weight for vector similarity score (0-1).
            fts_weight: Weight for FTS score (0-1).
            threshold: Minimum combined score threshold.

        Returns:
            List of (Memory, combined_score) tuples, sorted by relevance.
        """
        # Get vector search results (fetch more for merging)
        fetch_limit = max(50, limit * 3)
        vec_results = self.search_memories(
            query_embedding, limit=fetch_limit, threshold=0.2
        )

        # Get FTS results
        fts_results = self.search_fts(query_text, limit=fetch_limit)

        # Build score maps
        # Vector: convert distance to similarity (1 - distance)
        vec_scores: Dict[str, float] = {}
        vec_memories: Dict[str, Memory] = {}
        for memory, distance in vec_results:
            similarity = 1.0 - distance
            vec_scores[memory.id] = similarity
            vec_memories[memory.id] = memory

        # FTS: normalize BM25 scores (they are negative, lower is better)
        fts_scores: Dict[str, float] = {}
        if fts_results:
            # BM25 scores are negative, convert to 0-1 range
            min_score = min(score for _, score in fts_results)
            max_score = max(score for _, score in fts_results)
            score_range = max_score - min_score if max_score != min_score else 1.0

            for memory_id, score in fts_results:
                # Normalize: lower BM25 = better, so invert
                normalized = (
                    1.0 - (score - min_score) / score_range if score_range else 1.0
                )
                fts_scores[memory_id] = normalized

        # Combine scores using Reciprocal Rank Fusion (RRF) style merging
        all_ids = set(vec_scores.keys()) | set(fts_scores.keys())
        combined: List[Tuple[str, float]] = []

        for memory_id in all_ids:
            vec_score = vec_scores.get(memory_id, 0.0)
            fts_score = fts_scores.get(memory_id, 0.0)

            # Weighted combination
            final_score = (vec_score * vector_weight) + (fts_score * fts_weight)

            if final_score >= threshold:
                combined.append((memory_id, final_score))

        # Sort by combined score (descending)
        combined.sort(key=lambda x: x[1], reverse=True)

        # Fetch memories and return
        results: List[Tuple[Memory, float]] = []
        for memory_id, score in combined[:limit]:
            if memory_id in vec_memories:
                results.append((vec_memories[memory_id], score))
            else:
                # Fetch from DB if not in vector results
                memory = self.get_memory(memory_id)
                if memory:
                    results.append((memory, score))

        return results

    def add_processed_session(self, session: ProcessedSession):
        """Mark a session as processed."""
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO processed_sessions (
                    session_id, agent, processed_at, status, reason
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    session.session_id,
                    session.agent,
                    session.processed_at,
                    session.status,
                    session.reason,
                ),
            )

    def start_scan_run(
        self,
        scanner: str,
        agent: str,
        base_dir: Optional[str],
        incremental: bool,
        limit_value: int,
    ) -> str:
        """Create a scan run record and return its ID."""
        run_id = str(uuid.uuid4())
        started_at = int(time.time())
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO scan_runs (
                    id, scanner, agent, base_dir, incremental, limit_value, started_at,
                    status, total_files, scanned_files, skipped_unchanged,
                    unprocessed_sessions, error_count, limit_reached, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, NULL)
            """,
                (
                    run_id,
                    scanner,
                    agent,
                    base_dir,
                    1 if incremental else 0,
                    limit_value,
                    started_at,
                    "running",
                ),
            )
        return run_id

    def finalize_scan_run(
        self,
        run_id: str,
        *,
        status: str,
        total_files: int,
        scanned_files: int,
        skipped_unchanged: int,
        unprocessed_sessions: int,
        error_count: int,
        limit_reached: bool,
        note: Optional[str] = None,
    ) -> None:
        """Finalize a scan run with summary metrics."""
        finished_at = int(time.time())
        with self.conn:
            self.conn.execute(
                """
                UPDATE scan_runs SET
                    finished_at = ?,
                    status = ?,
                    total_files = ?,
                    scanned_files = ?,
                    skipped_unchanged = ?,
                    unprocessed_sessions = ?,
                    error_count = ?,
                    limit_reached = ?,
                    note = ?
                WHERE id = ?
            """,
                (
                    finished_at,
                    status,
                    total_files,
                    scanned_files,
                    skipped_unchanged,
                    unprocessed_sessions,
                    error_count,
                    1 if limit_reached else 0,
                    note,
                    run_id,
                ),
            )

    def add_scan_error(
        self,
        run_id: str,
        file_path: Optional[str],
        session_id: Optional[str],
        error_code: Optional[str],
        error_message: str,
    ) -> None:
        """Record a scan error for manual replay and diagnostics."""
        occurred_at = int(time.time())
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO scan_errors (
                    run_id, file_path, session_id, error_code, error_message, occurred_at,
                    resolved, resolved_at, resolution_note
                ) VALUES (?, ?, ?, ?, ?, ?, 0, NULL, NULL)
            """,
                (run_id, file_path, session_id, error_code, error_message, occurred_at),
            )

    def get_latest_scan_run(self, scanner: str, agent: str) -> Optional[Dict[str, Any]]:
        """Fetch the latest scan run for a scanner/agent."""
        cursor = self.conn.execute(
            """
            SELECT * FROM scan_runs
            WHERE scanner = ? AND agent = ?
            ORDER BY started_at DESC
            LIMIT 1
        """,
            (scanner, agent),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_scan_errors(
        self, *, limit: int = 50, unresolved_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get recent scan errors."""
        if unresolved_only:
            cursor = self.conn.execute(
                """
                SELECT * FROM scan_errors
                WHERE resolved = 0
                ORDER BY occurred_at DESC
                LIMIT ?
            """,
                (limit,),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT * FROM scan_errors
                ORDER BY occurred_at DESC
                LIMIT ?
            """,
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]

    def get_scan_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent scan run records."""
        cursor = self.conn.execute(
            """
            SELECT * FROM scan_runs
            ORDER BY started_at DESC
            LIMIT ?
        """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def resolve_scan_errors(
        self, ids: List[int], note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark scan errors as resolved with an optional note."""
        resolved: List[int] = []
        failed: List[int] = []
        resolved_at = int(time.time())

        with self.conn:
            for error_id in ids:
                cursor = self.conn.execute(
                    """
                    UPDATE scan_errors
                    SET resolved = 1,
                        resolved_at = ?,
                        resolution_note = ?
                    WHERE id = ?
                """,
                    (resolved_at, note, error_id),
                )
                if cursor.rowcount > 0:
                    resolved.append(error_id)
                else:
                    failed.append(error_id)

        return {"resolved": resolved, "failed": failed}

    def get_processed_session(
        self, session_id: str, agent: str
    ) -> Optional[ProcessedSession]:
        """Check if a session has been processed by a specific agent."""
        cursor = self.conn.execute(
            "SELECT * FROM processed_sessions WHERE session_id = ? AND agent = ?",
            (session_id, agent),
        )
        row = cursor.fetchone()
        if row:
            return ProcessedSession.from_dict(dict(row))
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM memories")
        memory_count = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM processed_sessions")
        session_count = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM scan_runs")
        scan_runs = cursor.fetchone()[0]

        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM scan_errors WHERE resolved = 0"
        )
        scan_errors = cursor.fetchone()[0]

        return {
            "memories": memory_count,
            "processed_sessions": session_count,
            "scan_runs": scan_runs,
            "scan_errors": scan_errors,
        }

    def touch_memory_access(self, memory_id: str) -> bool:
        """Increment access count for a memory and update access timestamp."""
        now = int(time.time())
        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE memories
                SET access_count = COALESCE(access_count, 0) + 1,
                    last_accessed_at = ?
                WHERE id = ?
                """,
                (now, memory_id),
            )
        return cursor.rowcount > 0

    def get_hot_memories(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most frequently accessed active memories."""
        cursor = self.conn.execute(
            """
            SELECT id, content, tags, importance, project_name,
                   created_at, updated_at, access_count, last_accessed_at
            FROM memories
            WHERE (superseded_by IS NULL OR superseded_by = '')
              AND COALESCE(access_count, 0) > 0
            ORDER BY access_count DESC, COALESCE(last_accessed_at, 0) DESC, updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._memory_row_to_summary(row) for row in cursor.fetchall()]

    def get_cold_memories(
        self, limit: int = 5, min_age_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get least accessed active memories that are old enough for curation."""
        cutoff = int(time.time()) - (min_age_days * 24 * 3600)
        cursor = self.conn.execute(
            """
            SELECT id, content, tags, importance, project_name,
                   created_at, updated_at, access_count, last_accessed_at
            FROM memories
            WHERE (superseded_by IS NULL OR superseded_by = '')
              AND created_at <= ?
            ORDER BY COALESCE(access_count, 0) ASC,
                     COALESCE(last_accessed_at, 0) ASC,
                     updated_at ASC
            LIMIT ?
            """,
            (cutoff, limit),
        )
        return [self._memory_row_to_summary(row) for row in cursor.fetchall()]

    def _memory_row_to_summary(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Build a compact summary payload for dashboard-oriented memory lists."""
        content = row["content"] or ""
        preview = content[:150] + "..." if len(content) > 150 else content

        tags_raw = row["tags"]
        if isinstance(tags_raw, str):
            try:
                tags = json.loads(tags_raw)
            except json.JSONDecodeError:
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        else:
            tags = tags_raw or []

        return {
            "id": row["id"],
            "preview": preview,
            "tags": tags,
            "importance": row["importance"],
            "project_name": row["project_name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "access_count": row["access_count"] or 0,
            "last_accessed_at": row["last_accessed_at"],
        }

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic information about database state.

        Returns:
            Dict with diagnostic information including:
            - vec_extension_loaded: Whether sqlite-vec loaded successfully
            - vec_load_error: Error message if loading failed
            - expected_dimension: Expected embedding dimension
            - vec_dimension_mismatch: Whether there's a dimension mismatch
            - schema_version: Current schema version
            - pending_migrations: Number of pending migrations
            - memory_count: Total memories in database
            - vec_count: Memories with embeddings
            - vec_tags_count: Memories with tag embeddings (dual index)
            - fts_count: Memories in FTS index
            - scan_runs: Total scan runs recorded
            - scan_errors: Unresolved scan errors
        """
        diag: Dict[str, Any] = {
            "vec_extension_loaded": self._vec_loaded,
            "vec_load_error": self._vec_load_error,
            "expected_dimension": self._embedding_dim,
            "vec_dimension_mismatch": False,
            "schema_version": 0,
            "pending_migrations": 0,
            "memory_count": 0,
            "vec_count": 0,
            "vec_tags_count": 0,
            "fts_count": 0,
            "scan_runs": 0,
            "scan_errors": 0,
        }

        try:
            # Get counts
            cursor = self.conn.execute("SELECT COUNT(*) FROM memories")
            diag["memory_count"] = cursor.fetchone()[0]

            cursor = self.conn.execute("SELECT COUNT(*) FROM vec_memories")
            diag["vec_count"] = cursor.fetchone()[0]

            # Get tag index count (may not exist)
            try:
                cursor = self.conn.execute("SELECT COUNT(*) FROM vec_tags")
                diag["vec_tags_count"] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                diag["vec_tags_count"] = 0

            cursor = self.conn.execute("SELECT COUNT(*) FROM memories_fts")
            diag["fts_count"] = cursor.fetchone()[0]

            cursor = self.conn.execute("SELECT COUNT(*) FROM scan_runs")
            diag["scan_runs"] = cursor.fetchone()[0]

            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM scan_errors WHERE resolved = 0"
            )
            diag["scan_errors"] = cursor.fetchone()[0]

            # Get migration status
            migration_status = get_migration_status(self.conn)
            diag["schema_version"] = migration_status["current_version"]
            diag["pending_migrations"] = migration_status["pending_count"]

            # Check dimension mismatch if we have vectors
            if diag["vec_count"] > 0 and self._vec_loaded:
                try:
                    test_vector = [0.0] * self._embedding_dim
                    test_blob = self._serialize_float32(test_vector)
                    self.conn.execute(
                        "SELECT memory_id FROM vec_memories WHERE embedding MATCH ? AND k = 1",
                        (test_blob,),
                    ).fetchone()
                except sqlite3.OperationalError:
                    diag["vec_dimension_mismatch"] = True

        except sqlite3.OperationalError as e:
            logger.debug(f"Diagnostics query error: {e}")

        return diag

    def close(self):
        self.conn.close()

    # ========================================================================
    # Extended methods for workflow/quick/dedupe commands (DatabasePort)
    # ========================================================================

    def is_session_processed(self, agent: str, session_id: str) -> bool:
        """Check if a session has been processed by a specific agent."""
        cursor = self.conn.execute(
            "SELECT 1 FROM processed_sessions WHERE agent = ? AND session_id = ?",
            (agent, session_id),
        )
        return cursor.fetchone() is not None

    def mark_session_processed(
        self,
        agent: str,
        session_id: str,
        status: str = "processed",
        reason: Optional[str] = None,
    ) -> None:
        """Mark a session as processed."""
        processed_at = int(time.time())
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO processed_sessions (
                    session_id, agent, processed_at, status, reason
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, agent, processed_at, status, reason),
            )

    def get_processed_session_count(self, agent: str) -> int:
        """Get count of processed sessions for an agent."""
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM processed_sessions WHERE agent = ?",
            (agent,),
        )
        return cursor.fetchone()[0]

    def get_unresolved_error_count(self) -> int:
        """Get count of unresolved scan errors."""
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM scan_errors WHERE resolved = 0"
        )
        return cursor.fetchone()[0]

    def delete_processed_sessions(self, agent: str, session_ids: List[str]) -> int:
        """Delete processed session records for an agent.

        Args:
            agent: Agent identifier.
            session_ids: Session IDs to delete.

        Returns:
            Number of deleted rows.
        """
        deleted = 0
        with self.conn:
            for session_id in session_ids:
                cursor = self.conn.execute(
                    "DELETE FROM processed_sessions WHERE agent = ? AND session_id = ?",
                    (agent, session_id),
                )
                if cursor.rowcount > 0:
                    deleted += cursor.rowcount
        return deleted

    def get_recent_memories(
        self,
        days: int = 7,
        limit: int = 10,
        project_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get memories updated within the last N days.

        Args:
            days: Look back N days.
            limit: Maximum results.
            project_path: Optional project filter.
            tags: Optional tag filter (memory must have all specified tags).

        Returns:
            List of memory dicts with preview and metadata.
        """
        cutoff = time.time() - (days * 24 * 3600)

        query = """
            SELECT id, content, tags, importance, project_path, 
                   created_at, updated_at
            FROM memories 
            WHERE updated_at >= ?
            AND (superseded_by IS NULL OR superseded_by = '')
        """
        params: List[Any] = [cutoff]

        if project_path:
            query += " AND project_path = ?"
            params.append(project_path)

        if tags:
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f"%{tag}%")

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()

        memories = []
        for row in rows:
            content = row["content"]
            # Parse tags from JSON array
            try:
                tags = json.loads(row["tags"]) if row["tags"] else []
            except (json.JSONDecodeError, TypeError):
                tags = (
                    [t.strip() for t in row["tags"].split(",")] if row["tags"] else []
                )
            memories.append(
                {
                    "id": row["id"],
                    "preview": content[:150] + "..." if len(content) > 150 else content,
                    "tags": tags,
                    "importance": row["importance"],
                    "project_path": row["project_path"],
                    "updated_at": row["updated_at"],
                    "age_hours": round((time.time() - row["updated_at"]) / 3600, 1),
                }
            )

        return memories

    def get_today_stats(self) -> Dict[str, Any]:
        """Get today's activity statistics.

        Returns:
            Dict with today's new/updated memories, active sessions, and recent items.
        """
        now = time.time()
        today_start = now - (now % 86400)  # Round down to midnight UTC

        # Count today's new memories
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE created_at >= ?",
            (today_start,),
        )
        new_memories = cursor.fetchone()[0]

        # Count today's updated memories (excluding new ones)
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE updated_at >= ? AND created_at < ?",
            (today_start, today_start),
        )
        updated_memories = cursor.fetchone()[0]

        # Count today's active sessions
        cursor = self.conn.execute(
            "SELECT COUNT(DISTINCT source_session_id) FROM memories WHERE created_at >= ?",
            (today_start,),
        )
        active_sessions = cursor.fetchone()[0]

        # Get recent memories (last 5)
        cursor = self.conn.execute(
            """
            SELECT id, content, tags, updated_at 
            FROM memories 
            WHERE updated_at >= ?
            ORDER BY updated_at DESC 
            LIMIT 5
            """,
            (today_start,),
        )

        recent = []
        for row in cursor:
            content = row["content"]
            # Parse tags from JSON array
            try:
                tags = json.loads(row["tags"]) if row["tags"] else []
            except (json.JSONDecodeError, TypeError):
                tags = (
                    [t.strip() for t in row["tags"].split(",")] if row["tags"] else []
                )
            recent.append(
                {
                    "id": row["id"],
                    "preview": content[:100] + "..." if len(content) > 100 else content,
                    "tags": tags,
                }
            )

        # Get total stats
        cursor = self.conn.execute("SELECT COUNT(*) FROM memories")
        total_memories = cursor.fetchone()[0]

        return {
            "date": time.strftime("%Y-%m-%d"),
            "today": {
                "new_memories": new_memories,
                "updated_memories": updated_memories,
                "active_sessions": active_sessions,
            },
            "recent_memories": recent,
            "total_memories": total_memories,
        }

    def find_memories_by_tag(
        self,
        tag: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Find memories containing a specific tag.

        Args:
            tag: Tag to search for.
            limit: Maximum results.

        Returns:
            List of memory dicts with content and metadata.
        """
        cursor = self.conn.execute(
            """
            SELECT id, content, tags, importance, project_path, updated_at
            FROM memories
            WHERE tags LIKE ?
            AND (superseded_by IS NULL OR superseded_by = '')
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (f"%{tag}%", limit),
        )

        memories = []
        for row in cursor:
            content = row["content"]
            # Parse tags from JSON array
            try:
                tags = json.loads(row["tags"]) if row["tags"] else []
            except (json.JSONDecodeError, TypeError):
                tags = (
                    [t.strip() for t in row["tags"].split(",")] if row["tags"] else []
                )
            memories.append(
                {
                    "id": row["id"],
                    "content": content,
                    "preview": content[:150] + "..." if len(content) > 150 else content,
                    "tags": tags,
                    "importance": row["importance"],
                    "project_path": row["project_path"],
                    "updated_at": row["updated_at"],
                }
            )

        return memories

    def get_all_tags(self, limit: int = 50) -> List[Tuple[str, int]]:
        """Get all unique tags with their counts.

        Args:
            limit: Maximum tags to return.

        Returns:
            List of (tag, count) tuples sorted by count descending.
        """
        cursor = self.conn.execute("""
            SELECT tags FROM memories 
            WHERE tags IS NOT NULL AND tags != ''
            AND (superseded_by IS NULL OR superseded_by = '')
        """)

        tag_counts: Dict[str, int] = {}
        for row in cursor:
            try:
                tags = json.loads(row["tags"])
            except (json.JSONDecodeError, TypeError):
                # Fallback for legacy comma-separated format
                tags = [t.strip() for t in row["tags"].split(",")]
            for tag in tags:
                tag = tag.strip() if isinstance(tag, str) else str(tag)
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by count descending, then alphabetically
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))[:limit]
        return sorted_tags

    def mark_memory_superseded(
        self,
        memory_id: str,
        superseded_by: str,
    ) -> None:
        """Mark a memory as superseded by another.

        This is a simple method that only updates the superseded_by field.
        Use supersede_memory() if you also need to add a new replacement memory.

        Args:
            memory_id: ID of the memory to mark as superseded.
            superseded_by: ID of the memory that supersedes it.
        """
        with self.conn:
            self.conn.execute(
                "UPDATE memories SET superseded_by = ?, updated_at = ? WHERE id = ?",
                (superseded_by, int(time.time()), memory_id),
            )
