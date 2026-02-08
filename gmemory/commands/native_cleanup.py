"""Cleanup native local ghost session records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from gmemory.scanner.base import ScannerRegistry
from gmemory.storage.database import MemoryDatabase
from gmemory.scanner import opencode, copilot  # noqa: F401


SCANNER_ALIASES = {
    "copilot": "github-copilot",
}


def _normalize_scanner_type(scanner_type: str) -> str:
    normalized = (scanner_type or "all").strip().lower()
    return SCANNER_ALIASES.get(normalized, normalized)


def _collect_opencode_session_ids(base_dir: Path) -> Tuple[Set[str], int, int]:
    ids: Set[str] = set()
    scanned_files = 0
    parse_errors = 0

    session_dir = base_dir / "storage" / "session"
    if not session_dir.exists() or not session_dir.is_dir():
        return ids, scanned_files, parse_errors

    for project_path in session_dir.iterdir():
        if not project_path.is_dir():
            continue
        for session_file in project_path.glob("ses_*.json"):
            scanned_files += 1
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                session_id = payload.get("id")
                if isinstance(session_id, str) and session_id.strip():
                    ids.add(session_id)
            except (json.JSONDecodeError, OSError):
                parse_errors += 1

    return ids, scanned_files, parse_errors


def _collect_copilot_session_ids(base_dir: Path) -> Tuple[Set[str], int, int]:
    ids: Set[str] = set()
    scanned_files = 0
    parse_errors = 0

    if not base_dir.exists() or not base_dir.is_dir():
        return ids, scanned_files, parse_errors

    for workspace_dir in base_dir.iterdir():
        if not workspace_dir.is_dir():
            continue
        chat_dir = workspace_dir / "chatSessions"
        if not chat_dir.exists() or not chat_dir.is_dir():
            continue
        for session_file in chat_dir.glob("*.json"):
            scanned_files += 1
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                session_id = payload.get("sessionId") or session_file.stem
                if isinstance(session_id, str) and session_id.strip():
                    ids.add(session_id)
            except (json.JSONDecodeError, OSError):
                parse_errors += 1

    return ids, scanned_files, parse_errors


def _collect_native_session_ids(
    scanner_name: str, scanner: Any
) -> Tuple[Set[str], int, int, bool]:
    base_dir = getattr(scanner, "base_dir", None)
    if base_dir is None:
        return set(), 0, 0, False

    path = Path(base_dir)
    if scanner_name == "opencode":
        ids, scanned_files, parse_errors = _collect_opencode_session_ids(path)
        return ids, scanned_files, parse_errors, True
    if scanner_name == "github-copilot":
        ids, scanned_files, parse_errors = _collect_copilot_session_ids(path)
        return ids, scanned_files, parse_errors, True

    return set(), 0, 0, False


def get_native_session_snapshot(scanner_name: str) -> Dict[str, Any]:
    """Collect local native session IDs and scan metadata for one scanner."""
    scanner = ScannerRegistry.create(
        name=scanner_name,
        incremental=False,
        agent=scanner_name,
    )
    if scanner is None:
        return {
            "scanner": scanner_name,
            "supported": False,
            "reason": "scanner_unavailable",
            "session_ids": set(),
            "native_files": 0,
            "parse_errors": 0,
        }

    session_ids, native_files, parse_errors, supported = _collect_native_session_ids(
        scanner_name,
        scanner,
    )
    if not supported:
        return {
            "scanner": scanner_name,
            "supported": False,
            "reason": "unsupported_native_cleanup",
            "session_ids": set(),
            "native_files": native_files,
            "parse_errors": parse_errors,
        }

    return {
        "scanner": scanner_name,
        "supported": True,
        "session_ids": session_ids,
        "native_files": native_files,
        "parse_errors": parse_errors,
    }


def cleanup_native_ghost_sessions(
    scanner_type: str = "all",
    dry_run: bool = True,
    limit: int = 5000,
    confirm_token: str | None = None,
) -> Dict[str, Any]:
    """Cleanup processed session markers that no longer exist on local scanners."""
    normalized_scanner = _normalize_scanner_type(scanner_type)
    available = sorted(ScannerRegistry.list_scanners())

    if normalized_scanner == "all":
        target_scanners = available
    elif normalized_scanner in available:
        target_scanners = [normalized_scanner]
    else:
        return {
            "error": f"Unknown scanner type: {scanner_type}. Available: {available}",
            "dry_run": dry_run,
            "scanner_type": normalized_scanner,
        }

    safe_limit = max(1, min(limit, 50000))
    scanned_processed_records = 0
    scanned_native_files = 0
    parse_errors = 0
    by_scanner: Dict[str, int] = {}
    details: List[Dict[str, Any]] = []
    would_delete: List[Dict[str, Any]] = []
    candidate_ids: Dict[str, List[str]] = {}

    db = MemoryDatabase()
    try:
        remaining = safe_limit
        for scanner_name in target_scanners:
            if remaining <= 0:
                break

            snapshot = get_native_session_snapshot(scanner_name)
            native_ids = snapshot["session_ids"]
            scanner_files = snapshot["native_files"]
            scanner_parse_errors = snapshot["parse_errors"]
            scanned_native_files += scanner_files
            parse_errors += scanner_parse_errors
            if not snapshot["supported"]:
                details.append(
                    {
                        "scanner": scanner_name,
                        "supported": False,
                        "reason": snapshot.get("reason", "unsupported_native_cleanup"),
                    }
                )
                continue

            processed_rows = db.list_processed_sessions(
                agent=scanner_name, limit=remaining
            )
            scanned_processed_records += len(processed_rows)
            remaining -= len(processed_rows)

            scanner_candidates: List[str] = []
            for row in processed_rows:
                session_id = str(row.get("session_id") or "")
                if not session_id:
                    continue
                if session_id not in native_ids:
                    scanner_candidates.append(session_id)
                    if len(would_delete) < 200:
                        would_delete.append(
                            {
                                "session_id": session_id,
                                "agent": scanner_name,
                                "reason": "missing_local_session",
                            }
                        )

            candidate_ids[scanner_name] = scanner_candidates
            by_scanner[scanner_name] = len(scanner_candidates)
            details.append(
                {
                    "scanner": scanner_name,
                    "supported": True,
                    "native_files": scanner_files,
                    "processed_records": len(processed_rows),
                    "candidate_count": len(scanner_candidates),
                    "parse_errors": scanner_parse_errors,
                }
            )

        candidate_count = sum(len(items) for items in candidate_ids.values())
        limit_reached = remaining <= 0
        expected_confirm_token = (
            f"confirm-native-cleanup:{normalized_scanner}:{safe_limit}"
        )
        by_reason = {"missing_local_session": candidate_count}

        total_processed_before_cleanup = 0
        for scanner_name in target_scanners:
            total_processed_before_cleanup += db.get_processed_session_count(
                scanner_name
            )

        if dry_run:
            return {
                "dry_run": True,
                "scanner_type": normalized_scanner,
                "scanned_processed_records": scanned_processed_records,
                "scanned_native_files": scanned_native_files,
                "candidate_count": candidate_count,
                "would_delete": would_delete,
                "by_scanner": by_scanner,
                "by_reason": by_reason,
                "parse_errors": parse_errors,
                "limit_reached": limit_reached,
                "details": details,
                "confirm_token": expected_confirm_token,
                "total_processed_before_cleanup": total_processed_before_cleanup,
                "total_processed_after": total_processed_before_cleanup,
                "summary": f"Would delete {candidate_count} local ghost processed-session records.",
            }

        if confirm_token != expected_confirm_token:
            return {
                "dry_run": False,
                "scanner_type": normalized_scanner,
                "error": "confirm_token required for apply; run dry_run first",
                "error_code": "VALIDATION_ERROR",
                "expected_confirm_token": expected_confirm_token,
                "candidate_count": candidate_count,
                "by_scanner": by_scanner,
                "by_reason": by_reason,
                "total_processed_before_cleanup": total_processed_before_cleanup,
                "total_processed_after": total_processed_before_cleanup,
            }

        deleted = 0
        failed: List[Dict[str, Any]] = []
        for scanner_name, session_ids in candidate_ids.items():
            if not session_ids:
                continue
            try:
                deleted += db.delete_processed_sessions(
                    agent=scanner_name,
                    session_ids=session_ids,
                )
            except Exception as exc:
                failed.append(
                    {
                        "scanner": scanner_name,
                        "count": len(session_ids),
                        "error": str(exc),
                    }
                )

        total_processed_after = 0
        for scanner_name in target_scanners:
            total_processed_after += db.get_processed_session_count(scanner_name)

        return {
            "dry_run": False,
            "scanner_type": normalized_scanner,
            "scanned_processed_records": scanned_processed_records,
            "scanned_native_files": scanned_native_files,
            "candidate_count": candidate_count,
            "deleted": deleted,
            "failed": failed,
            "by_scanner": by_scanner,
            "by_reason": by_reason,
            "parse_errors": parse_errors,
            "limit_reached": limit_reached,
            "details": details,
            "confirm_token": expected_confirm_token,
            "total_processed_before_cleanup": total_processed_before_cleanup,
            "total_processed_after": total_processed_after,
            "summary": f"Deleted {deleted} local ghost processed-session records.",
        }
    finally:
        db.close()
