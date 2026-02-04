"""Source adapters for GMemory.

Provides a pluggable architecture for parsing different agent log formats.
Each adapter handles a specific log format and converts it to the common
Session/Message model.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from gmemory.models import Session, Message

logger = logging.getLogger(__name__)


@dataclass
class SourceInfo:
    """Information about a source adapter."""

    name: str
    description: str
    default_path: str
    file_pattern: str
    supported: bool = True


class SourceAdapter(ABC):
    """Abstract base class for source adapters.

    Source adapters handle parsing of specific log formats and converting
    them to the common Session/Message model used by GMemory.

    Implement this interface to add support for new agent log formats.
    """

    # Adapter identifier
    name: str = "base"

    # Human-readable description
    description: str = "Base adapter"

    # Default data directory (relative to home or absolute)
    default_path: str = ""

    # File pattern for session files
    file_pattern: str = "*.json"

    @abstractmethod
    def parse_session_file(self, file_path: Path) -> Optional[Session]:
        """Parse a session file and return a Session object.

        Args:
            file_path: Path to the session file.

        Returns:
            Session object or None if parsing fails.
        """
        pass

    @abstractmethod
    def parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """Parse message data and return a Message object.

        Args:
            data: Raw message data from the log file.

        Returns:
            Message object or None if parsing fails.
        """
        pass

    @abstractmethod
    def get_session_id(self, file_path: Path, data: Dict[str, Any]) -> Optional[str]:
        """Extract session ID from file path or data.

        Args:
            file_path: Path to the session file.
            data: Parsed session data.

        Returns:
            Session ID string or None.
        """
        pass

    def get_default_base_dir(self) -> Path:
        """Get the default base directory for this adapter.

        Returns:
            Path to the default data directory.
        """
        if self.default_path.startswith("~"):
            return Path(self.default_path).expanduser()
        elif self.default_path.startswith("/") or (
            len(self.default_path) > 1 and self.default_path[1] == ":"
        ):
            return Path(self.default_path)
        else:
            return Path.home() / self.default_path

    def get_info(self) -> SourceInfo:
        """Get information about this adapter.

        Returns:
            SourceInfo dataclass.
        """
        return SourceInfo(
            name=self.name,
            description=self.description,
            default_path=self.default_path,
            file_pattern=self.file_pattern,
            supported=True,
        )


class SourceAdapterRegistry:
    """Registry for source adapters.

    Allows dynamic registration and lookup of adapters by name.
    """

    _adapters: Dict[str, Type[SourceAdapter]] = {}

    @classmethod
    def register(cls, adapter_class: Type[SourceAdapter]) -> Type[SourceAdapter]:
        """Register a source adapter class.

        Can be used as a decorator:
            @SourceAdapterRegistry.register
            class MyAdapter(SourceAdapter):
                name = "my_agent"
                ...

        Args:
            adapter_class: Adapter class to register.

        Returns:
            The adapter class (for decorator usage).
        """
        name = adapter_class.name
        if name in cls._adapters:
            logger.warning(f"Overwriting existing adapter: {name}")
        cls._adapters[name] = adapter_class
        logger.debug(f"Registered source adapter: {name}")
        return adapter_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[SourceAdapter]]:
        """Get an adapter class by name.

        Args:
            name: Adapter identifier.

        Returns:
            Adapter class or None if not found.
        """
        return cls._adapters.get(name)

    @classmethod
    def create(cls, name: str) -> Optional[SourceAdapter]:
        """Create an adapter instance by name.

        Args:
            name: Adapter identifier.

        Returns:
            Adapter instance or None if not found.
        """
        adapter_class = cls.get(name)
        if adapter_class is None:
            logger.error(f"Unknown source adapter: {name}")
            return None
        return adapter_class()

    @classmethod
    def list_adapters(cls) -> List[str]:
        """List all registered adapter names.

        Returns:
            List of adapter names.
        """
        return list(cls._adapters.keys())

    @classmethod
    def get_all_info(cls) -> List[SourceInfo]:
        """Get information about all registered adapters.

        Returns:
            List of SourceInfo objects.
        """
        infos = []
        for name in sorted(cls._adapters.keys()):
            adapter = cls.create(name)
            if adapter:
                infos.append(adapter.get_info())
        return infos


# ============================================================================
# Built-in Adapters
# ============================================================================


@SourceAdapterRegistry.register
class OpenCodeAdapter(SourceAdapter):
    """Adapter for OpenCode session logs."""

    name = "opencode"
    description = "OpenCode AI coding assistant logs"
    default_path = ".local/share/opencode/storage"
    file_pattern = "ses_*.json"

    def parse_session_file(self, file_path: Path) -> Optional[Session]:
        """Parse OpenCode session file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            session_id = self.get_session_id(file_path, data)
            if not session_id:
                return None

            return Session(
                session_id=session_id,
                agent="opencode",
                project_path=data.get("directory", ""),
                project_name=data.get("title", ""),
                started_at=str(data.get("time", {}).get("created", "")),
                messages=[],  # Messages loaded separately
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to parse OpenCode session: {e}")
            return None

    def parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """Parse OpenCode message data."""
        msg_id = data.get("id")
        if not msg_id:
            return None

        role = data.get("role", "unknown")
        content = data.get("content", "")

        return Message(role=role, content=content)

    def get_session_id(self, file_path: Path, data: Dict[str, Any]) -> Optional[str]:
        """Extract session ID from OpenCode data."""
        return data.get("id") or file_path.stem


@SourceAdapterRegistry.register
class ClaudeCodeAdapter(SourceAdapter):
    """Adapter for Claude Code (claude-mem) session logs.

    Note: This is a placeholder for future implementation.
    Claude Code uses a different storage format with SQLite + hooks.
    """

    name = "claude-code"
    description = "Claude Code assistant logs (placeholder)"
    default_path = ".claude-code"
    file_pattern = "*.json"

    def parse_session_file(self, file_path: Path) -> Optional[Session]:
        """Parse Claude Code session file."""
        # Placeholder - Claude Code uses SQLite, not JSON files
        logger.warning("Claude Code adapter is a placeholder. Use claude-mem directly.")
        return None

    def parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """Parse Claude Code message data."""
        return None

    def get_session_id(self, file_path: Path, data: Dict[str, Any]) -> Optional[str]:
        """Extract session ID."""
        return data.get("id")

    def get_info(self) -> SourceInfo:
        """Mark as not fully supported."""
        info = super().get_info()
        info.supported = False
        return info


@SourceAdapterRegistry.register
class CodexCLIAdapter(SourceAdapter):
    """Adapter for OpenAI Codex CLI session logs.

    Parses session files from ~/.codex/sessions/ directory.
    """

    name = "codex"
    description = "OpenAI Codex CLI session logs"
    default_path = ".codex/sessions"
    file_pattern = "*.jsonl"

    def parse_session_file(self, file_path: Path) -> Optional[Session]:
        """Parse Codex CLI session file (JSONL format)."""
        try:
            messages = []
            session_id = None
            project_path = ""
            started_at = ""

            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)

                        # Extract session metadata from first entry
                        if session_id is None:
                            session_id = data.get("session_id") or file_path.stem
                            project_path = (
                                data.get("cwd") or data.get("directory") or ""
                            )
                            started_at = str(
                                data.get("timestamp") or data.get("created_at") or ""
                            )

                        # Parse message
                        msg = self.parse_message(data)
                        if msg:
                            messages.append(msg)

                    except json.JSONDecodeError:
                        continue

            if not session_id:
                session_id = file_path.stem

            return Session(
                session_id=session_id,
                agent="codex",
                project_path=project_path,
                project_name=Path(project_path).name if project_path else "",
                started_at=started_at,
                messages=messages,
            )

        except OSError as e:
            logger.warning(f"Failed to parse Codex session: {e}")
            return None

    def parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """Parse Codex CLI message data."""
        # Codex uses 'type' for role (user, assistant, system)
        role = data.get("type") or data.get("role") or "unknown"

        # Content can be in different fields
        content = data.get("content") or data.get("message") or data.get("text") or ""

        if not content:
            return None

        return Message(role=str(role), content=str(content))

    def get_session_id(self, file_path: Path, data: Dict[str, Any]) -> Optional[str]:
        """Extract session ID from Codex data."""
        return data.get("session_id") or data.get("id") or file_path.stem


@SourceAdapterRegistry.register
class CursorAdapter(SourceAdapter):
    """Adapter for Cursor IDE conversation logs.

    Parses conversation history from Cursor's storage directory.
    """

    name = "cursor"
    description = "Cursor IDE conversation logs"
    default_path = ".cursor/conversations"
    file_pattern = "*.json"

    def parse_session_file(self, file_path: Path) -> Optional[Session]:
        """Parse Cursor conversation file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            session_id = self.get_session_id(file_path, data)
            if not session_id:
                return None

            messages = []
            msg_data = data.get("messages") or data.get("conversation") or []
            for msg in msg_data:
                parsed = self.parse_message(msg)
                if parsed:
                    messages.append(parsed)

            return Session(
                session_id=session_id,
                agent="cursor",
                project_path=data.get("workspaceFolder") or data.get("directory") or "",
                project_name=data.get("title") or data.get("name") or "",
                started_at=str(data.get("createdAt") or data.get("timestamp") or ""),
                messages=messages,
            )

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to parse Cursor conversation: {e}")
            return None

    def parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """Parse Cursor message data."""
        role = data.get("role") or data.get("type") or "unknown"
        content = data.get("content") or data.get("text") or ""

        if not content:
            return None

        # Handle structured content (Cursor sometimes uses arrays)
        if isinstance(content, list):
            content = "\n".join(
                str(c.get("text", c)) if isinstance(c, dict) else str(c)
                for c in content
            )

        return Message(role=str(role), content=str(content))

    def get_session_id(self, file_path: Path, data: Dict[str, Any]) -> Optional[str]:
        """Extract session ID from Cursor data."""
        return data.get("id") or data.get("conversationId") or file_path.stem

    def get_info(self) -> SourceInfo:
        """Mark as experimental."""
        info = super().get_info()
        info.description = "Cursor IDE conversation logs (experimental)"
        return info


@SourceAdapterRegistry.register
class AiderAdapter(SourceAdapter):
    """Adapter for Aider chat history logs.

    Parses chat history from Aider's .aider.chat.history.md files.
    """

    name = "aider"
    description = "Aider chat history logs"
    default_path = ""  # Aider stores in project root
    file_pattern = ".aider.chat.history.md"

    def parse_session_file(self, file_path: Path) -> Optional[Session]:
        """Parse Aider chat history file (Markdown format)."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Aider uses markdown format with role headers
            messages = self._parse_markdown_chat(content)

            # Use parent directory as project path
            project_path = str(file_path.parent.absolute())

            # Generate session ID from file path hash
            import hashlib

            session_id = f"aider_{hashlib.md5(project_path.encode()).hexdigest()[:12]}"

            return Session(
                session_id=session_id,
                agent="aider",
                project_path=project_path,
                project_name=file_path.parent.name,
                started_at="",  # Aider doesn't store timestamps in history
                messages=messages,
            )

        except OSError as e:
            logger.warning(f"Failed to parse Aider history: {e}")
            return None

    def _parse_markdown_chat(self, content: str) -> List[Message]:
        """Parse Aider's markdown chat format."""
        messages = []
        current_role = None
        current_content = []

        for line in content.split("\n"):
            # Aider uses headers like "#### user" or "#### assistant"
            if line.startswith("#### "):
                # Save previous message
                if current_role and current_content:
                    messages.append(
                        Message(
                            role=current_role,
                            content="\n".join(current_content).strip(),
                        )
                    )

                current_role = line[5:].strip().lower()
                current_content = []
            elif current_role:
                current_content.append(line)

        # Save last message
        if current_role and current_content:
            messages.append(
                Message(role=current_role, content="\n".join(current_content).strip())
            )

        return messages

    def parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """Parse message data (not used for Aider - uses markdown parsing)."""
        return None

    def get_session_id(self, file_path: Path, data: Dict[str, Any]) -> Optional[str]:
        """Extract session ID."""
        import hashlib

        project_path = str(file_path.parent.absolute())
        return f"aider_{hashlib.md5(project_path.encode()).hexdigest()[:12]}"

    def get_info(self) -> SourceInfo:
        """Mark as experimental."""
        info = super().get_info()
        info.description = "Aider chat history logs (experimental)"
        return info


@SourceAdapterRegistry.register
class GenericJSONAdapter(SourceAdapter):
    """Generic adapter for JSON-based session logs.

    Attempts to parse common JSON structures used by various agents.
    Useful for custom or unknown formats.
    """

    name = "generic"
    description = "Generic JSON session logs (auto-detect structure)"
    default_path = ""
    file_pattern = "*.json"

    def parse_session_file(self, file_path: Path) -> Optional[Session]:
        """Parse generic JSON session file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            session_id = self.get_session_id(file_path, data)
            if not session_id:
                return None

            # Try common field names
            messages = []
            msg_data = (
                data.get("messages")
                or data.get("conversation")
                or data.get("history")
                or []
            )

            for msg in msg_data:
                parsed = self.parse_message(msg)
                if parsed:
                    messages.append(parsed)

            return Session(
                session_id=session_id,
                agent="generic",
                project_path=data.get("directory")
                or data.get("project")
                or data.get("path")
                or "",
                project_name=data.get("title") or data.get("name") or "",
                started_at=str(
                    data.get("created_at")
                    or data.get("timestamp")
                    or data.get("time")
                    or ""
                ),
                messages=messages,
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to parse generic session: {e}")
            return None

    def parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """Parse generic message data."""
        # Try common field names for role
        role = data.get("role") or data.get("type") or data.get("sender") or "unknown"

        # Try common field names for content
        content = data.get("content") or data.get("text") or data.get("message") or ""

        if not content:
            return None

        return Message(role=str(role), content=str(content))

    def get_session_id(self, file_path: Path, data: Dict[str, Any]) -> Optional[str]:
        """Extract session ID from various possible fields."""
        return (
            data.get("id")
            or data.get("session_id")
            or data.get("conversation_id")
            or file_path.stem
        )


# ============================================================================
# Helper Functions
# ============================================================================


def list_sources() -> Dict[str, Any]:
    """List all available source adapters.

    Returns:
        Dict with adapter information.
    """
    adapters = SourceAdapterRegistry.get_all_info()

    return {
        "adapters": [
            {
                "name": a.name,
                "description": a.description,
                "default_path": a.default_path,
                "file_pattern": a.file_pattern,
                "supported": a.supported,
            }
            for a in adapters
        ],
        "total": len(adapters),
        "supported": sum(1 for a in adapters if a.supported),
    }


def detect_source(path: Path) -> Optional[str]:
    """Attempt to detect the source type from a directory.

    Args:
        path: Directory path to analyze.

    Returns:
        Adapter name if detected, None otherwise.
    """
    if not path.exists():
        return None

    # Check for OpenCode structure
    if (path / "session").exists() and (path / "message").exists():
        return "opencode"

    # Check for common patterns
    json_files = list(path.glob("*.json"))
    if json_files:
        # Try to parse first file and detect structure
        try:
            with open(json_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)

            # OpenCode-style
            if "directory" in data and "time" in data:
                return "opencode"

            # Generic with messages
            if "messages" in data or "conversation" in data:
                return "generic"
        except Exception:
            pass

    return "generic"  # Default fallback


def get_source_info(name: str) -> Dict[str, Any]:
    """Get detailed information about a source adapter.

    Args:
        name: Adapter name.

    Returns:
        Dict with adapter details or error.
    """
    adapter = SourceAdapterRegistry.create(name)
    if not adapter:
        return {
            "error": f"Unknown source adapter: '{name}'",
            "available": SourceAdapterRegistry.list_adapters(),
        }

    info = adapter.get_info()
    base_dir = adapter.get_default_base_dir()

    return {
        "name": info.name,
        "description": info.description,
        "default_path": info.default_path,
        "resolved_path": str(base_dir),
        "path_exists": base_dir.exists(),
        "file_pattern": info.file_pattern,
        "supported": info.supported,
    }
