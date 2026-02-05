"""Simple dependency injection container for GMemory.

Provides lazy initialization and singleton management for core components.
Enables easy testing by allowing mock injection.
"""

from typing import Optional

from gmemory.ports import ConfigPort, DatabasePort, EmbedderPort


class Container:
    """Simple dependency injection container.

    Manages singleton instances of core components with lazy initialization.
    Supports mock injection for testing.

    Usage:
        # Production code
        container = get_container()
        db = container.get_database()
        embedder = container.get_embedder()

        # Test code
        container = get_container()
        container.set_database(mock_db)
        container.set_embedder(mock_embedder)
    """

    _instance: Optional["Container"] = None
    _database: Optional[DatabasePort] = None
    _embedder: Optional[EmbedderPort] = None
    _config: Optional[ConfigPort] = None

    def __new__(cls) -> "Container":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "Container":
        """Get the singleton container instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_database(self) -> DatabasePort:
        """Get database instance, creating if needed.

        Returns:
            DatabasePort implementation (MemoryDatabase by default).
        """
        if self._database is None:
            from gmemory.storage.database import MemoryDatabase

            # Use embedder dimension for consistency
            embedder = self.get_embedder()
            self._database = MemoryDatabase(embedding_dimension=embedder.dimension)
        return self._database

    def get_embedder(self) -> EmbedderPort:
        """Get embedder instance, creating if needed.

        Returns:
            EmbedderPort implementation (FastEmbedder/NoOpEmbedder by default).
        """
        if self._embedder is None:
            from gmemory.storage.embedder import get_embedder

            self._embedder = get_embedder()
        return self._embedder

    def get_config(self) -> ConfigPort:
        """Get config instance, creating if needed.

        Returns:
            ConfigPort implementation (Config singleton by default).
        """
        if self._config is None:
            from gmemory.config import config

            self._config = config
        return self._config

    # Testing support methods

    def set_database(self, db: DatabasePort) -> None:
        """Inject a database implementation (for testing).

        Args:
            db: Database implementation to use.
        """
        self._database = db

    def set_embedder(self, embedder: EmbedderPort) -> None:
        """Inject an embedder implementation (for testing).

        Args:
            embedder: Embedder implementation to use.
        """
        self._embedder = embedder

    def set_config(self, cfg: ConfigPort) -> None:
        """Inject a config implementation (for testing).

        Args:
            cfg: Config implementation to use.
        """
        self._config = cfg

    def reset(self) -> None:
        """Reset all cached instances.

        Useful for testing to ensure clean state between tests.
        """
        if self._database is not None:
            try:
                self._database.close()
            except Exception:
                pass
        self._database = None
        self._embedder = None
        self._config = None

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance entirely.

        Use with caution - mainly for testing isolation.
        """
        if cls._instance is not None:
            cls._instance.reset()
        cls._instance = None


def get_container() -> Container:
    """Get the global container instance.

    This is the primary entry point for dependency access.

    Returns:
        The singleton Container instance.
    """
    return Container.get_instance()
