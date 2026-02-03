import sqlite3
import struct
import json
import time
from typing import List, Optional, Tuple, Any, Dict
from pathlib import Path
import sqlite_vec

from gmemory.config import config
from gmemory.models import Memory, ProcessedSession


class MemoryDatabase:
    """
    SQLite-based storage for memories using sqlite-vec for vector search.
    """

    def __init__(self):
        self.db_path = config.db_path
        self._ensure_db_dir()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Load sqlite-vec extension
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)

        self._configure_pragma()
        self._init_tables()

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
            dim = config.embedding_dimension
            self.conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories USING vec0(
                    memory_id TEXT PRIMARY KEY,
                    embedding float32[{dim}] distance_metric=cosine
                );
            """)

            # Processed sessions tracking
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_sessions (
                    session_id TEXT,
                    agent TEXT,
                    processed_at INTEGER NOT NULL,
                    PRIMARY KEY (agent, session_id)
                );
            """)

    def _serialize_float32(self, vector: List[float]) -> bytes:
        """Serialize a list of floats into a binary blob for sqlite-vec."""
        return struct.pack(f"{len(vector)}f", *vector)

    def add_memory(self, memory: Memory, embedding: Optional[List[float]] = None):
        """Add a memory and its embedding to the database."""
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

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by ID."""
        cursor = self.conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if row:
            return Memory.from_dict(dict(row))
        return None

    def update_memory(self, memory: Memory, embedding: Optional[List[float]] = None):
        """Update an existing memory."""
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

    def delete_memory(self, memory_id: str):
        """Delete a memory."""
        with self.conn:
            self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self.conn.execute(
                "DELETE FROM vec_memories WHERE memory_id = ?", (memory_id,)
            )

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

    def add_processed_session(self, session: ProcessedSession):
        """Mark a session as processed."""
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO processed_sessions (session_id, agent, processed_at)
                VALUES (?, ?, ?)
            """,
                (session.session_id, session.agent, session.processed_at),
            )

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

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM memories")
        memory_count = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM processed_sessions")
        session_count = cursor.fetchone()[0]

        return {"memories": memory_count, "processed_sessions": session_count}

    def close(self):
        self.conn.close()
