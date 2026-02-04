import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict
from contextlib import closing

from gmemory.config import config
from gmemory.models import Session, Message
from gmemory.storage.database import MemoryDatabase
from gmemory.scanner.state import ScanStateManager
from gmemory.scanner.base import Scanner, ScannerRegistry
from gmemory.utils.privacy import strip_private_tags

logger = logging.getLogger(__name__)


@ScannerRegistry.register
class OpenCodeScanner(Scanner):
    """
    Scans OpenCode storage for sessions and messages.
    Supports incremental scanning to skip unchanged files.
    """

    name = "opencode"

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        incremental: bool = True,
        agent: Optional[str] = None,
    ):
        """Initialize scanner.

        Args:
            base_dir: Base directory for OpenCode data. Defaults to standard location.
            incremental: Enable incremental scanning (skip unchanged files).
            agent: Agent identifier for filtering. Defaults to config.default_agent.
        """
        # Set default base_dir before calling super().__init__
        if base_dir is None:
            base_dir = Path.home() / ".local" / "share" / "opencode"

        super().__init__(base_dir=base_dir, agent=agent, incremental=incremental)

        # base_dir is guaranteed non-None at this point
        self.storage_dir = base_dir / "storage"
        self._state_manager = ScanStateManager() if incremental else None

    def get_unprocessed_sessions(self, limit: int = 10) -> List[Session]:
        """
        Retrieves a list of sessions that have not yet been processed by the current agent.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of Session objects.
        """
        sessions: List[Session] = []
        agent = self.agent
        skipped_unchanged = 0
        scanned_files = 0
        error_count = 0
        run_id: Optional[str] = None

        session_dir = self.storage_dir / "session"
        if not session_dir.exists():
            with closing(MemoryDatabase()) as db:
                run_id = db.start_scan_run(
                    scanner=self.name,
                    agent=agent,
                    base_dir=str(self.base_dir) if self.base_dir else None,
                    incremental=self.incremental,
                    limit_value=limit,
                )
                db.finalize_scan_run(
                    run_id=run_id,
                    status="completed",
                    total_files=0,
                    scanned_files=0,
                    skipped_unchanged=0,
                    unprocessed_sessions=0,
                    error_count=0,
                    limit_reached=False,
                    note="session directory not found",
                )
            return []

        # Load incremental state if enabled
        state = self._state_manager.load() if self._state_manager else None

        # We need to check against the database to see if processed
        with closing(MemoryDatabase()) as db:
            run_id = db.start_scan_run(
                scanner=self.name,
                agent=agent,
                base_dir=str(self.base_dir) if self.base_dir else None,
                incremental=self.incremental,
                limit_value=limit,
            )

            total_files = 0
            for project_path in session_dir.iterdir():
                if project_path.is_dir():
                    total_files += len(list(project_path.glob("ses_*.json")))

            # Walk through project directories
            for project_path in session_dir.iterdir():
                if not project_path.is_dir():
                    continue

                # Walk through session files in project directory
                for session_file in project_path.glob("ses_*.json"):
                    if len(sessions) >= limit:
                        self._save_state()
                        if skipped_unchanged > 0:
                            logger.debug(f"Skipped {skipped_unchanged} unchanged files")
                        db.finalize_scan_run(
                            run_id=run_id,
                            status="partial",
                            total_files=total_files,
                            scanned_files=scanned_files,
                            skipped_unchanged=skipped_unchanged,
                            unprocessed_sessions=len(sessions),
                            error_count=error_count,
                            limit_reached=True,
                            note="limit reached",
                        )
                        return sessions

                    try:
                        # Incremental check: skip unchanged files
                        if state and not state.is_file_changed(session_file):
                            skipped_unchanged += 1
                            continue

                        scanned_files += 1

                        session_id = session_file.stem  # e.g., "ses_123"
                        # The file stem includes 'ses_', but the ID might be just the suffix depending on how it's stored.
                        # Looking at learnings: "storage/session/<projectID>/ses_<sessionID>.json"
                        # Usually ID is the whole "ses_..." or just the part after.
                        # Let's inspect the file content to be sure about the ID.

                        # Optimization: Check DB first if we can verify the ID convention.
                        # But safely, let's read the JSON first to get the *actual* ID field.

                        with open(session_file, "r", encoding="utf-8") as f:
                            session_data = json.load(f)

                        actual_session_id = session_data.get("id")
                        if not actual_session_id:
                            # Update state even for invalid files to skip next time
                            if state:
                                state.update_file_state(session_file, "")
                            continue

                        # Check if processed
                        if db.get_processed_session(actual_session_id, agent):
                            # Already processed - update state and skip
                            if state:
                                state.update_file_state(session_file, actual_session_id)
                            continue

                        # It is unprocessed, let's load full session details
                        full_session = self._load_full_session(
                            actual_session_id, session_data
                        )
                        if full_session:
                            sessions.append(full_session)
                            # Note: Don't update state here - only after successful processing

                    except (json.JSONDecodeError, OSError) as e:
                        error_count += 1
                        db.add_scan_error(
                            run_id=run_id,
                            file_path=str(session_file),
                            session_id=None,
                            error_code="GMEM-SCN-302",
                            error_message=str(e),
                        )
                        logger.warning(
                            f"Failed to read session file {session_file}: {e}"
                        )
                        continue

        self._save_state()
        if skipped_unchanged > 0:
            logger.debug(f"Skipped {skipped_unchanged} unchanged files")
        if run_id:
            with closing(MemoryDatabase()) as db:
                db.finalize_scan_run(
                    run_id=run_id,
                    status="completed",
                    total_files=total_files,
                    scanned_files=scanned_files,
                    skipped_unchanged=skipped_unchanged,
                    unprocessed_sessions=len(sessions),
                    error_count=error_count,
                    limit_reached=False,
                    note=None,
                )
        return sessions

    def mark_session_scanned(self, session_file: Path, session_id: str) -> None:
        """Mark a session file as scanned (update incremental state).

        Call this after successfully processing a session.
        """
        if self._state_manager:
            state = self._state_manager.load()
            state.update_file_state(session_file, session_id)
            self._state_manager.save()

    def _save_state(self) -> None:
        """Save incremental state to disk."""
        if self._state_manager:
            self._state_manager.save()

    def _load_full_session(
        self, session_id: str, session_metadata: Dict
    ) -> Optional[Session]:
        """Loads messages and parts for a given session."""

        # Message directory: storage/message/ses_<sessionID>/
        # Note: The folder name usually matches the session file stem or ID.
        # Based on learnings: "storage/message/ses_<sessionID>/msg_<messageID>.json"
        # It implies the folder is "ses_<sessionID>".
        # We need to be careful if session_id inside JSON differs from filename.
        # Usually folder name matches the filename stem of the session file.
        # Let's try to construct path using the ID from metadata first.

        # We need to handle the "ses_" prefix.
        # If session_id is "123", folder is likely "ses_123".
        # If session_id is "ses_123", folder is "ses_123".

        # Strategy: Look for directory matching `ses_{session_id}` or just `{session_id}`
        # or verify with the session_file's parent structure.
        # But here we are looking into `storage/message/`.

        # Let's assume the folder name in `storage/message` corresponds to the session ID
        # but possibly with a prefix.
        # If the metadata ID is "ulid", the folder is likely "ses_ulid".

        msg_dir_name = (
            f"ses_{session_id}" if not session_id.startswith("ses_") else session_id
        )
        msg_base_dir = self.storage_dir / "message" / msg_dir_name

        if not msg_base_dir.exists():
            # Fallback: maybe the ID in metadata includes "ses_" already?
            # Or the folder doesn't have it?
            # Let's try without prefix if it had one, or vice versa.
            if session_id.startswith("ses_"):
                alt_dir = self.storage_dir / "message" / session_id[4:]
                if alt_dir.exists():
                    msg_base_dir = alt_dir
            else:
                # Already tried adding prefix, maybe raw ID?
                alt_dir = self.storage_dir / "message" / session_id
                if alt_dir.exists():
                    msg_base_dir = alt_dir

        if not msg_base_dir.exists():
            # No messages found, return session without messages?
            # Or return None? Return Session with empty messages.
            return self._create_session_obj(session_metadata, [])

        messages: List[Message] = []

        # Iterate over message files
        for msg_file in sorted(msg_base_dir.glob("msg_*.json")):
            try:
                with open(msg_file, "r", encoding="utf-8") as f:
                    msg_data = json.load(f)

                msg_id = msg_data.get("id")
                if not msg_id:
                    continue

                role = msg_data.get("role", "unknown")

                # Load content parts
                content = self._load_message_content(msg_id)

                if content:
                    messages.append(Message(role=role, content=content))

            except (json.JSONDecodeError, OSError):
                continue

        return self._create_session_obj(session_metadata, messages)

    def _load_message_content(self, message_id: str) -> str:
        """Loads and concatenates text parts for a message."""
        # Parts dir: storage/part/msg_<messageID>/

        part_dir_name = (
            f"msg_{message_id}" if not message_id.startswith("msg_") else message_id
        )
        part_base_dir = self.storage_dir / "part" / part_dir_name

        if not part_base_dir.exists():
            if message_id.startswith("msg_"):
                alt_dir = self.storage_dir / "part" / message_id[4:]
                if alt_dir.exists():
                    part_base_dir = alt_dir
            else:
                alt_dir = self.storage_dir / "part" / message_id
                if alt_dir.exists():
                    part_base_dir = alt_dir

        if not part_base_dir.exists():
            return ""

        parts_content = []

        # Sort by filename to ensure order
        for part_file in sorted(part_base_dir.glob("prt_*.json")):
            try:
                with open(part_file, "r", encoding="utf-8") as f:
                    part_data = json.load(f)

                # Check type
                if part_data.get("type") == "text":
                    text = part_data.get("text", "")
                    if text:
                        parts_content.append(text)
                # We could handle tool usage here, but MVP might just want text.
                # Requirement: "Parse message parts and concatenate text content"
                # If there are other types (like tool_use), we might skip or include representations.
                # For now, let's stick to 'text' field if present.
                # Some parts might be code blocks which are also text.

            except (json.JSONDecodeError, OSError):
                continue

        full_text = "".join(parts_content)
        return self._clean_text(full_text)

    def _clean_text(self, text: str) -> str:
        """Clean text content, preserving Unicode (Chinese, etc.) and stripping private tags."""
        if not text:
            return ""

        # First strip private content
        cleaned, stripped_count = strip_private_tags(text)
        if stripped_count > 0:
            logger.debug(f"Stripped {stripped_count} private tag(s) from content")

        # Handle None case (shouldn't happen with non-empty input, but be safe)
        if cleaned is None:
            cleaned = ""

        # Only remove control characters, keep all printable Unicode
        import unicodedata

        return "".join(
            char
            for char in cleaned
            if not unicodedata.category(char).startswith("C") or char in "\n\t"
        )

    def _create_session_obj(self, metadata: Dict, messages: List[Message]) -> Session:
        """Helper to create Session object from metadata and messages."""
        return Session(
            session_id=metadata.get("id", ""),
            agent=self.agent,  # Use scanner's agent setting
            project_path=metadata.get(
                "directory", ""
            ),  # 'directory' field in session json
            project_name=metadata.get("title", ""),  # 'title' field
            started_at=str(metadata.get("time", {}).get("created", "")),
            messages=messages,
        )

    def get_scan_stats(self) -> Dict[str, int]:
        """Get statistics about scan state.

        Returns:
            Dict with keys: total_files, tracked_files
        """
        session_dir = self.storage_dir / "session"
        total_files = 0

        if session_dir.exists():
            for project_path in session_dir.iterdir():
                if project_path.is_dir():
                    total_files += len(list(project_path.glob("ses_*.json")))

        tracked_files = 0
        if self._state_manager:
            state = self._state_manager.load()
            tracked_files = len(state.files)

        return {
            "total_session_files": total_files,
            "tracked_files": tracked_files,
        }

    def count_sessions(self) -> int:
        """Count total number of session files (lightweight, no content loading).

        Returns:
            Total session count.
        """
        session_dir = self.storage_dir / "session"
        total = 0

        if session_dir.exists():
            for project_path in session_dir.iterdir():
                if project_path.is_dir():
                    total += len(list(project_path.glob("ses_*.json")))

        return total
