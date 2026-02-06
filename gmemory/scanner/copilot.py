"""GitHub Copilot Chat session scanner.

Scans VS Code workspaceStorage chatSessions for Copilot chat logs.
"""

import json
import logging
import os
from contextlib import closing
from pathlib import Path
from typing import Dict, List, Optional

from gmemory.config import config
from gmemory.models import Session, Message
from gmemory.storage.database import MemoryDatabase
from gmemory.scanner.base import Scanner, ScannerRegistry
from gmemory.scanner.state import ScanStateManager
from gmemory.utils.privacy import strip_private_tags

logger = logging.getLogger(__name__)


@ScannerRegistry.register
class CopilotScanner(Scanner):
    """Scans GitHub Copilot Chat sessions from VS Code workspace storage."""

    name = "github-copilot"

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        incremental: bool = True,
        agent: Optional[str] = None,
    ):
        if base_dir is None:
            base_dir = (
                Path.home()
                / "AppData"
                / "Roaming"
                / "Code"
                / "User"
                / "workspaceStorage"
            )

        super().__init__(base_dir=base_dir, agent=agent, incremental=incremental)
        self._state_manager = ScanStateManager() if incremental else None

    def get_unprocessed_sessions(self, limit: int = 10) -> List[Session]:
        sessions: List[Session] = []
        agent = self.agent
        skipped_unchanged = 0
        scanned_files = 0
        error_count = 0
        run_id: Optional[str] = None

        chat_dirs = list(self._iter_chat_dirs())
        if not chat_dirs:
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
                    note="chatSessions directory not found",
                )
            return []

        state = self._state_manager.load() if self._state_manager else None

        with closing(MemoryDatabase()) as db:
            run_id = db.start_scan_run(
                scanner=self.name,
                agent=agent,
                base_dir=str(self.base_dir) if self.base_dir else None,
                incremental=self.incremental,
                limit_value=limit,
            )

            total_files = sum(
                len(list(chat_dir.glob("*.json"))) for chat_dir in chat_dirs
            )

            for chat_dir in chat_dirs:
                for session_file in chat_dir.glob("*.json"):
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
                        if state and not state.is_file_changed(session_file):
                            skipped_unchanged += 1
                            continue

                        scanned_files += 1

                        with open(session_file, "r", encoding="utf-8") as f:
                            session_data = json.load(f)

                        session_id = session_data.get("sessionId") or session_file.stem
                        if not session_id:
                            if state:
                                state.update_file_state(session_file, "")
                            continue

                        if db.get_processed_session(session_id, agent):
                            if state:
                                state.update_file_state(session_file, session_id)
                            continue

                        session = self._load_full_session(
                            session_id, session_data, session_file
                        )
                        if session:
                            sessions.append(session)

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
                            f"Failed to read Copilot session file {session_file}: {e}"
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

    def count_sessions(self) -> int:
        total = 0
        for chat_dir in self._iter_chat_dirs():
            total += len(list(chat_dir.glob("*.json")))
        return total

    def get_scan_stats(self) -> Dict[str, int]:
        total_files = self.count_sessions()
        tracked_files = 0
        if self._state_manager:
            tracked_files = len(self._state_manager.load().files)
        return {
            "total_session_files": total_files,
            "tracked_files": tracked_files,
        }

    def _iter_chat_dirs(self) -> List[Path]:
        if not self.base_dir or not self.base_dir.exists():
            return []
        chat_dirs = []
        for workspace_dir in self.base_dir.iterdir():
            if not workspace_dir.is_dir():
                continue
            chat_dir = workspace_dir / "chatSessions"
            if chat_dir.exists() and chat_dir.is_dir():
                chat_dirs.append(chat_dir)
        return chat_dirs

    def _load_full_session(
        self, session_id: str, session_data: Dict, session_file: Path
    ) -> Optional[Session]:
        messages: List[Message] = []

        for request in session_data.get("requests", []):
            user_text = self._extract_user_text(request)
            if user_text:
                messages.append(Message(role="user", content=user_text))

            assistant_texts = self._extract_assistant_texts(request)
            for text in assistant_texts:
                messages.append(Message(role="assistant", content=text))

        project_path = self._resolve_workspace_path(session_file)
        project_name = os.path.basename(project_path) if project_path else ""
        started_at = str(session_data.get("creationDate", ""))

        return Session(
            session_id=session_id,
            agent=self.agent,
            project_path=project_path or "",
            project_name=project_name,
            started_at=started_at,
            messages=messages,
        )

    def _extract_user_text(self, request: Dict) -> str:
        message = request.get("message", {}) if isinstance(request, dict) else {}
        text = ""
        if isinstance(message, dict):
            text = message.get("text", "") or ""
        return self._clean_text(text)

    def _extract_assistant_texts(self, request: Dict) -> List[str]:
        responses = request.get("response", []) if isinstance(request, dict) else []
        texts: List[str] = []
        if not isinstance(responses, list):
            responses = [responses]
        for resp in responses:
            if not isinstance(resp, dict):
                continue
            kind = resp.get("kind", "")
            if kind in {
                "thinking",
                "toolInvocation",
                "toolInvocationSerialized",
                "prepareToolInvocation",
                "mcpServersStarting",
            }:
                continue
            value = resp.get("value") or resp.get("text")
            if isinstance(value, str) and value.strip():
                cleaned = self._clean_text(value)
                if cleaned:
                    texts.append(cleaned)
        return texts

    def _resolve_workspace_path(self, session_file: Path) -> str:
        workspace_dir = session_file.parent.parent
        workspace_file = workspace_dir / "workspace.json"
        if not workspace_file.exists():
            return ""
        try:
            with open(workspace_file, "r", encoding="utf-8") as f:
                workspace_data = json.load(f)
            folder_uri = workspace_data.get("folder") or ""
            return self._decode_workspace_uri(folder_uri)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read workspace.json {workspace_file}: {e}")
            return ""

    def _decode_workspace_uri(self, folder_uri: str) -> str:
        if not folder_uri:
            return ""
        if folder_uri.startswith("file:///"):
            uri = folder_uri[len("file:///") :]
            from urllib.parse import unquote

            decoded = unquote(uri)
            return decoded.replace("/", "\\")
        return folder_uri

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""

        cleaned, stripped_count = strip_private_tags(text)
        if stripped_count > 0:
            logger.debug(f"Stripped {stripped_count} private tag(s) from content")

        if cleaned is None:
            cleaned = ""

        import unicodedata

        return "".join(
            char
            for char in cleaned
            if not unicodedata.category(char).startswith("C") or char in "\n\t"
        )

    def _save_state(self) -> None:
        if self._state_manager:
            self._state_manager.save()
