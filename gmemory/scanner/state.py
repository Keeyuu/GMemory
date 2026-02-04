"""Incremental scan state management for GMemory.

Tracks file state (size, mtime, content_hash) to avoid re-processing unchanged sessions.
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def compute_file_hash(path: Path, max_bytes: int = 64 * 1024) -> str:
    """Compute a fast hash of file content.

    Args:
        path: Path to file.
        max_bytes: Maximum bytes to read for hashing (default 64KB).
                   For larger files, samples beginning and end.

    Returns:
        MD5 hex digest of sampled content.
    """
    try:
        file_size = path.stat().st_size
        hasher = hashlib.md5()

        with open(path, "rb") as f:
            if file_size <= max_bytes:
                # Small file: hash entire content
                hasher.update(f.read())
            else:
                # Large file: hash beginning + end
                hasher.update(f.read(max_bytes // 2))
                f.seek(-max_bytes // 2, 2)  # Seek from end
                hasher.update(f.read())

        return hasher.hexdigest()
    except OSError:
        return ""


@dataclass
class FileState:
    """State of a single scanned file."""

    path: str  # Absolute path to file
    size: int  # File size in bytes
    mtime: float  # Modification time (Unix timestamp)
    inode: int = 0  # Inode number (for rotation detection, 0 on Windows)
    content_hash: str = ""  # MD5 hash of file content (for content change detection)
    last_session_id: str = ""  # Last processed session ID from this file

    @classmethod
    def from_path(
        cls, path: Path, session_id: str = "", compute_hash: bool = True
    ) -> "FileState":
        """Create FileState from a file path."""
        stat = path.stat()
        try:
            inode = stat.st_ino
        except AttributeError:
            inode = 0  # Windows doesn't have inode

        content_hash = compute_file_hash(path) if compute_hash else ""

        return cls(
            path=str(path.absolute()),
            size=stat.st_size,
            mtime=stat.st_mtime,
            inode=inode,
            content_hash=content_hash,
            last_session_id=session_id,
        )


@dataclass
class ScanState:
    """Persistent state for incremental scanning.

    Stores file states indexed by path to detect changes.
    """

    version: int = 1
    files: Dict[str, FileState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Convert dict entries to FileState if loaded from JSON
        if self.files:
            converted = {}
            for path, state in self.files.items():
                if isinstance(state, dict):
                    converted[path] = FileState(**state)
                else:
                    converted[path] = state
            self.files = converted

    def get_file_state(self, path: Path) -> Optional[FileState]:
        """Get stored state for a file."""
        return self.files.get(str(path.absolute()))

    def update_file_state(self, path: Path, session_id: str = "") -> None:
        """Update state for a file after processing."""
        state = FileState.from_path(path, session_id)
        self.files[state.path] = state

    def remove_file_state(self, path: Path) -> None:
        """Remove state for a deleted file."""
        key = str(path.absolute())
        if key in self.files:
            del self.files[key]

    def is_file_changed(self, path: Path) -> bool:
        """Check if a file has changed since last scan.

        Returns True if:
        - File is new (not in state)
        - File size changed
        - File mtime changed
        - File content hash changed (detects in-place edits)
        - File was truncated (size < previous, indicates rotation/reset)
        """
        stored = self.get_file_state(path)
        if stored is None:
            return True  # New file

        try:
            current_stat = path.stat()
        except OSError:
            return True  # File might be deleted or inaccessible

        # Size changed
        if current_stat.st_size != stored.size:
            return True

        # Modification time changed
        if current_stat.st_mtime != stored.mtime:
            return True

        # Content hash changed (catches in-place edits with same size/mtime)
        if stored.content_hash:
            current_hash = compute_file_hash(path)
            if current_hash and current_hash != stored.content_hash:
                logger.debug(f"Content hash changed for {path}")
                return True

        return False

    def is_file_truncated(self, path: Path) -> bool:
        """Check if file was truncated (e.g., log rotation with copytruncate)."""
        stored = self.get_file_state(path)
        if stored is None:
            return False

        try:
            current_stat = path.stat()
            return current_stat.st_size < stored.size
        except OSError:
            return False


class ScanStateManager:
    """Manages persistence of scan state to disk."""

    def __init__(self, state_path: Optional[Path] = None) -> None:
        """Initialize state manager.

        Args:
            state_path: Path to state file. Defaults to ~/.gmemory/scan_state.json
        """
        if state_path:
            self.state_path = state_path
        else:
            self.state_path = Path.home() / ".gmemory" / "scan_state.json"

        self._state: Optional[ScanState] = None

    def load(self) -> ScanState:
        """Load state from disk or create new."""
        if self._state is not None:
            return self._state

        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._state = ScanState(**data)
                logger.debug(f"Loaded scan state with {len(self._state.files)} files")
            except (json.JSONDecodeError, OSError, TypeError) as e:
                logger.warning(f"Failed to load scan state: {e}, starting fresh")
                self._state = ScanState()
        else:
            self._state = ScanState()

        return self._state

    def save(self) -> None:
        """Save current state to disk."""
        if self._state is None:
            return

        # Ensure directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize to JSON
        data = {
            "version": self._state.version,
            "files": {path: asdict(state) for path, state in self._state.files.items()},
        }

        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved scan state with {len(self._state.files)} files")
        except OSError as e:
            logger.error(f"Failed to save scan state: {e}")

    def cleanup_missing_files(self) -> int:
        """Remove state entries for files that no longer exist.

        Returns:
            Number of entries removed.
        """
        state = self.load()
        missing = [path for path in state.files.keys() if not Path(path).exists()]

        for path in missing:
            del state.files[path]

        if missing:
            logger.info(f"Cleaned up {len(missing)} missing file entries")
            self.save()

        return len(missing)
