"""Scanner base class and registry for GMemory.

Provides an extensible architecture for supporting multiple agent types.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Type

from gmemory.models import Session

logger = logging.getLogger(__name__)


class Scanner(ABC):
    """Abstract base class for session scanners.

    Implement this interface to add support for new agent types.
    """

    # Scanner identifier (e.g., "opencode", "cursor", "aider")
    name: str = "base"

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        agent: Optional[str] = None,
        incremental: bool = True,
    ):
        """Initialize scanner.

        Args:
            base_dir: Base directory for agent data.
            agent: Agent identifier for filtering processed sessions.
            incremental: Enable incremental scanning (skip unchanged files).
        """
        self.base_dir = base_dir
        self.agent = agent or self.name
        self.incremental = incremental

    @abstractmethod
    def get_unprocessed_sessions(self, limit: int = 10) -> List[Session]:
        """Retrieve unprocessed sessions.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of Session objects.
        """
        pass

    @abstractmethod
    def count_sessions(self) -> int:
        """Count total number of session files (lightweight, no content loading).

        Returns:
            Total session count.
        """
        pass

    def get_scan_stats(self) -> Dict[str, int]:
        """Get scanning statistics.

        Returns:
            Dict with scanner-specific stats.
        """
        return {"total_sessions": self.count_sessions()}


class ScannerRegistry:
    """Registry for scanner implementations.

    Allows dynamic registration and lookup of scanners by name.
    """

    _scanners: Dict[str, Type[Scanner]] = {}

    @classmethod
    def register(cls, scanner_class: Type[Scanner]) -> Type[Scanner]:
        """Register a scanner class.

        Can be used as a decorator:
            @ScannerRegistry.register
            class MyScanner(Scanner):
                name = "my_agent"
                ...

        Args:
            scanner_class: Scanner class to register.

        Returns:
            The scanner class (for decorator usage).
        """
        name = scanner_class.name
        if name in cls._scanners:
            logger.warning(f"Overwriting existing scanner: {name}")
        cls._scanners[name] = scanner_class
        logger.debug(f"Registered scanner: {name}")
        return scanner_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[Scanner]]:
        """Get a scanner class by name.

        Args:
            name: Scanner identifier.

        Returns:
            Scanner class or None if not found.
        """
        return cls._scanners.get(name)

    @classmethod
    def create(
        cls,
        name: str,
        base_dir: Optional[Path] = None,
        agent: Optional[str] = None,
        incremental: bool = True,
    ) -> Optional[Scanner]:
        """Create a scanner instance by name.

        Args:
            name: Scanner identifier.
            base_dir: Base directory override.
            agent: Agent identifier override.
            incremental: Enable incremental scanning.

        Returns:
            Scanner instance or None if not found.
        """
        scanner_class = cls.get(name)
        if scanner_class is None:
            logger.error(f"Unknown scanner type: {name}")
            return None
        return scanner_class(base_dir=base_dir, agent=agent, incremental=incremental)

    @classmethod
    def list_scanners(cls) -> List[str]:
        """List all registered scanner names.

        Returns:
            List of scanner names.
        """
        return list(cls._scanners.keys())
