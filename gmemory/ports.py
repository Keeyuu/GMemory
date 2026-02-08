"""Protocol interfaces for GMemory dependency injection.

Defines abstract interfaces (Protocols) for core components to enable:
- Loose coupling between layers
- Easy testing with mock implementations
- Clear contracts for each component

Interface Segregation (ISP):
- MemoryReadPort: Read operations (get, list, browse)
- MemoryWritePort: Write operations (add, update, delete)
- MemorySearchPort: Search operations (vector, FTS, hybrid)
- WorkflowPort: Session workflow operations
- DiagnosticsPort: Stats and health checks
- DatabasePort: Composite interface for backward compatibility
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from gmemory.models import Memory, ProcessedSession


# =============================================================================
# Segregated Interfaces (ISP-compliant)
# =============================================================================


@runtime_checkable
class MemoryReadPort(Protocol):
    """Read operations for memories.

    Single responsibility: Retrieve memories without modification.
    """

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID."""
        ...

    def get_active_memories(
        self,
        limit: int = 100,
        offset: int = 0,
        project_path: Optional[str] = None,
    ) -> List[Memory]:
        """Get active (non-superseded) memories."""
        ...

    def get_recent_memories(
        self,
        days: int = 7,
        limit: int = 10,
        project_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get memories updated within the last N days."""
        ...

    def find_memories_by_tag(
        self,
        tag: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Find memories containing a specific tag."""
        ...

    def get_all_tags(self, limit: int = 50) -> List[Tuple[str, int]]:
        """Get all unique tags with their counts."""
        ...

    def get_hot_memories(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most frequently accessed memories."""
        ...

    def get_cold_memories(
        self, limit: int = 5, min_age_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get least accessed memories for curation."""
        ...


@runtime_checkable
class MemoryWritePort(Protocol):
    """Write operations for memories.

    Single responsibility: Create, update, delete memories.
    """

    def add_memory(
        self,
        memory: Memory,
        embedding: Optional[List[float]] = None,
        tag_embedding: Optional[List[float]] = None,
        validate: bool = True,
    ) -> None:
        """Add a memory to the database."""
        ...

    def update_memory(
        self,
        memory: Memory,
        embedding: Optional[List[float]] = None,
        tag_embedding: Optional[List[float]] = None,
    ) -> None:
        """Update an existing memory."""
        ...

    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory by ID."""
        ...

    def mark_memory_superseded(
        self,
        memory_id: str,
        superseded_by: str,
    ) -> None:
        """Mark a memory as superseded by another."""
        ...

    def touch_memory_access(self, memory_id: str) -> bool:
        """Increment access count for a memory."""
        ...


@runtime_checkable
class MemorySearchPort(Protocol):
    """Search operations for memories.

    Single responsibility: Vector, FTS, and hybrid search.
    """

    def search_memories(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.0,
        project_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_superseded: bool = False,
    ) -> List[Tuple[Memory, float]]:
        """Search memories by vector similarity."""
        ...

    def search_fts(
        self,
        query: str,
        limit: int = 10,
        project_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_superseded: bool = False,
    ) -> List[Tuple[str, float]]:
        """Search memories using full-text search."""
        ...

    def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        limit: int = 10,
        vector_weight: float = 0.7,
        fts_weight: float = 0.3,
        project_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_superseded: bool = False,
    ) -> List[Tuple[Memory, float]]:
        """Combined vector + FTS search."""
        ...

    def search_tags(
        self,
        tag_embedding: List[float],
        limit: int = 50,
    ) -> List[Tuple[str, float]]:
        """Search memories by tag similarity."""
        ...

    def has_tag_index(self) -> bool:
        """Check if the tag index exists and has data."""
        ...


@runtime_checkable
class WorkflowPort(Protocol):
    """Session workflow operations.

    Single responsibility: Track session processing state and errors.
    """

    def is_session_processed(self, agent: str, session_id: str) -> bool:
        """Check if a session has been processed."""
        ...

    def mark_session_processed(
        self,
        agent: str,
        session_id: str,
        status: str = "processed",
        reason: Optional[str] = None,
        source_updated_at: Optional[int] = None,
        session_hash: Optional[str] = None,
        processor: str = "default",
        run_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> None:
        """Mark a session as processed."""
        ...

    def get_latest_processed_session(
        self,
        agent: str,
        session_id: str,
        processor: str = "default",
    ) -> Optional[Dict[str, Any]]:
        """Get latest processed-state row for one session."""
        ...

    def get_processed_session_count(self, agent: str) -> int:
        """Get count of processed sessions for an agent."""
        ...

    def get_unresolved_error_count(self) -> int:
        """Get count of unresolved scan errors."""
        ...

    def delete_processed_sessions(self, agent: str, session_ids: List[str]) -> int:
        """Delete processed session records for an agent."""
        ...

    def get_scan_errors(
        self,
        limit: int = 100,
        unresolved_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get scan errors with optional filtering."""
        ...

    def resolve_scan_errors(
        self,
        error_ids: List[int],
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve scan errors by IDs."""
        ...


@runtime_checkable
class DiagnosticsPort(Protocol):
    """Diagnostics and statistics operations.

    Single responsibility: Health checks, stats, and lifecycle management.
    """

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        ...

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic information."""
        ...

    def get_today_stats(self) -> Dict[str, Any]:
        """Get today's activity statistics."""
        ...

    def close(self) -> None:
        """Close database connection."""
        ...


# =============================================================================
# Composite Interface (Backward Compatibility)
# =============================================================================


@runtime_checkable
class DatabasePort(
    MemoryReadPort,
    MemoryWritePort,
    MemorySearchPort,
    WorkflowPort,
    DiagnosticsPort,
    Protocol,
):
    """Composite database interface for backward compatibility.

    Combines all segregated interfaces into a single facade.
    Existing code using DatabasePort continues to work unchanged.

    For new code, prefer using the specific ports:
    - MemoryReadPort for read-only operations
    - MemoryWritePort for mutations
    - MemorySearchPort for search operations
    - WorkflowPort for session management
    - DiagnosticsPort for health checks
    """

    pass


class EmbedderPort(Protocol):
    """Embedding operations interface.

    Defines the contract for text embedding generation.
    """

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        ...

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        ...

    def to_blob(self, embedding: List[float]) -> bytes:
        """Convert embedding to binary blob for storage."""
        ...


class ConfigPort(Protocol):
    """Configuration access interface.

    Defines the contract for accessing configuration values.
    """

    @property
    def db_path(self) -> Path:
        """Database file path."""
        ...

    @property
    def embedding_provider(self) -> str:
        """Embedding provider name."""
        ...

    @property
    def embedding_model(self) -> str:
        """Embedding model name."""
        ...

    @property
    def embedding_dimension(self) -> int:
        """Embedding vector dimension."""
        ...

    @property
    def embedding_cache_dir(self) -> Optional[str]:
        """Embedding model cache directory."""
        ...

    @property
    def embedding_active_profile(self) -> str:
        """Active embedding profile name."""
        ...

    @property
    def default_agent(self) -> str:
        """Default scanner agent."""
        ...

    @property
    def search_default_mode(self) -> str:
        """Default search mode (hybrid/vector/fts)."""
        ...

    @property
    def search_default_profile(self) -> str:
        """Default search profile name."""
        ...

    @property
    def search_default_limit(self) -> int:
        """Default search result limit."""
        ...

    @property
    def search_vector_weight(self) -> float:
        """Vector search weight in hybrid mode."""
        ...

    @property
    def search_fts_weight(self) -> float:
        """FTS search weight in hybrid mode."""
        ...

    @property
    def search_recency_weight(self) -> float:
        """Recency weight in search scoring."""
        ...

    @property
    def search_recency_window_days(self) -> int:
        """Recency window in days."""
        ...

    @property
    def search_min_score_threshold(self) -> float:
        """Minimum score threshold for results."""
        ...

    @property
    def search_use_tag_index(self) -> bool:
        """Whether to use tag index in search."""
        ...

    @property
    def search_tag_weight(self) -> float:
        """Tag similarity weight in search."""
        ...

    @property
    def lifecycle_retention_days(self) -> int:
        """Memory retention period in days."""
        ...

    @property
    def lifecycle_archive_before_purge(self) -> bool:
        """Whether to archive before purging."""
        ...
