"""External provider data import for web/CLI workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from gmemory.scanner.base import ScannerRegistry
from gmemory.storage.database import MemoryDatabase
from gmemory.scanner import opencode, copilot  # noqa: F401


SCANNER_ALIASES = {
    "copilot": "github-copilot",
}


def _normalize_scanner_type(scanner_type: str) -> str:
    normalized = (scanner_type or "").strip().lower()
    return SCANNER_ALIASES.get(normalized, normalized)


def import_external_provider_data(
    folder_path: str,
    scanner_type: str,
    limit: int = 500,
) -> Dict[str, Any]:
    normalized_scanner = _normalize_scanner_type(scanner_type)
    source_dir = Path(folder_path).expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        return {
            "queued": 0,
            "updated": 0,
            "imported": 0,
            "failed": 0,
            "error": f"Folder path does not exist: {source_dir}",
        }

    scanner = ScannerRegistry.create(
        name=normalized_scanner,
        base_dir=source_dir,
        agent=normalized_scanner,
        incremental=False,
    )
    if scanner is None:
        available_scanners = sorted(ScannerRegistry.list_scanners())
        return {
            "queued": 0,
            "updated": 0,
            "imported": 0,
            "failed": 0,
            "error": (
                f"Unknown scanner type: {scanner_type}. "
                f"Available: {available_scanners}. "
                "Tip: use 'github-copilot' for Copilot logs."
            ),
        }

    source_total_sessions = scanner.count_sessions()
    sessions = scanner.get_unprocessed_sessions(limit=limit)
    queued = 0
    updated = 0
    failed = 0
    errors: List[Dict[str, str]] = []
    total_imported_sessions = 0
    pending_unprocessed = 0

    db = MemoryDatabase()
    try:
        for session in sessions:
            if not session.session_id:
                failed += 1
                errors.append(
                    {
                        "session_id": "",
                        "error": "Missing session_id",
                    }
                )
                continue

            try:
                created = db.upsert_imported_session(
                    session=session,
                    source_scanner=normalized_scanner,
                    source_path=str(source_dir),
                )
                if created:
                    queued += 1
                else:
                    updated += 1
            except Exception as exc:
                failed += 1
                errors.append(
                    {
                        "session_id": session.session_id,
                        "error": str(exc),
                    }
                )

        total_imported_sessions = db.count_imported_sessions(normalized_scanner)
        pending_unprocessed = db.count_unprocessed_imported_sessions(normalized_scanner)
    finally:
        db.close()

    return {
        "queued": queued,
        "updated": updated,
        "imported": queued,
        "failed": failed,
        "total_sessions": len(sessions),
        "source_total_sessions": source_total_sessions,
        "scanner_type": normalized_scanner,
        "folder_path": str(source_dir),
        "pending_unprocessed": pending_unprocessed,
        "processed_sessions": max(0, total_imported_sessions - pending_unprocessed),
        "total_imported_sessions": total_imported_sessions,
        "errors": errors[:20],
    }
