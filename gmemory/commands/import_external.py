"""External provider data import for web/CLI workflows."""

from __future__ import annotations

import json
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from gmemory.scanner.base import ScannerRegistry
from gmemory.storage.database import MemoryDatabase
from gmemory.scanner import opencode, copilot  # noqa: F401


SCANNER_ALIASES = {
    "copilot": "github-copilot",
}


def _normalize_scanner_type(scanner_type: str) -> str:
    normalized = (scanner_type or "").strip().lower()
    return SCANNER_ALIASES.get(normalized, normalized)


def _prepare_external_scanner(
    folder_path: str,
    scanner_type: str,
) -> Dict[str, Any]:
    normalized_scanner = _normalize_scanner_type(scanner_type)
    source_dir = Path(folder_path).expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        return {
            "ok": False,
            "normalized_scanner": normalized_scanner,
            "source_dir": source_dir,
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
            "ok": False,
            "normalized_scanner": normalized_scanner,
            "source_dir": source_dir,
            "error": (
                f"Unknown scanner type: {scanner_type}. "
                f"Available: {available_scanners}. "
                "Tip: use 'github-copilot' for Copilot logs."
            ),
        }

    return {
        "ok": True,
        "normalized_scanner": normalized_scanner,
        "source_dir": source_dir,
        "scanner": scanner,
    }


def _collect_opencode_source_ids(source_dir: Path) -> Tuple[Set[str], int, int]:
    session_ids: Set[str] = set()
    scanned_files = 0
    parse_errors = 0

    session_dir = source_dir / "storage" / "session"
    if not session_dir.exists() or not session_dir.is_dir():
        return session_ids, scanned_files, parse_errors

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
                    session_ids.add(session_id)
            except (json.JSONDecodeError, OSError):
                parse_errors += 1

    return session_ids, scanned_files, parse_errors


def _coerce_source_updated_at(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = int(value)
        if ts > 10_000_000_000:
            ts = ts // 1000
        return ts
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            ts = int(text)
            if ts > 10_000_000_000:
                ts = ts // 1000
            return ts
    return None


def _compute_source_version(payload: Dict[str, Any]) -> Tuple[int | None, str]:
    time_info = payload.get("time")
    source_updated_at = None
    if isinstance(time_info, dict):
        source_updated_at = _coerce_source_updated_at(
            time_info.get("updated")
            or time_info.get("modified")
            or time_info.get("lastUpdated")
            or time_info.get("created")
        )
    if source_updated_at is None:
        source_updated_at = _coerce_source_updated_at(
            payload.get("lastModified") or payload.get("creationDate")
        )

    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    session_hash = hashlib.md5(canonical.encode("utf-8")).hexdigest()
    return source_updated_at, session_hash


def _is_processed_for_source_version(
    latest: Dict[str, Any] | None,
    source_updated_at: int | None,
    session_hash: str,
) -> bool:
    if latest is None:
        return False

    latest_updated_raw = latest.get("source_updated_at")
    latest_hash = latest.get("session_hash")
    latest_updated = int(latest_updated_raw) if latest_updated_raw is not None else None

    if latest_updated is None and not latest_hash:
        return False
    if source_updated_at is not None and latest_updated is None:
        return False
    if (
        source_updated_at is not None
        and latest_updated is not None
        and source_updated_at > latest_updated
    ):
        return False
    if latest_hash is None:
        return False
    if session_hash != latest_hash:
        return False
    return True


def _collect_opencode_source_versions(
    source_dir: Path,
) -> Tuple[Dict[str, Dict[str, Any]], int, int]:
    versions: Dict[str, Dict[str, Any]] = {}
    scanned_files = 0
    parse_errors = 0

    session_dir = source_dir / "storage" / "session"
    if not session_dir.exists() or not session_dir.is_dir():
        return versions, scanned_files, parse_errors

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
                    source_updated_at, session_hash = _compute_source_version(payload)
                    versions[session_id] = {
                        "source_updated_at": source_updated_at,
                        "session_hash": session_hash,
                    }
            except (json.JSONDecodeError, OSError):
                parse_errors += 1

    return versions, scanned_files, parse_errors


def _collect_copilot_source_versions(
    source_dir: Path,
) -> Tuple[Dict[str, Dict[str, Any]], int, int]:
    versions: Dict[str, Dict[str, Any]] = {}
    scanned_files = 0
    parse_errors = 0

    if not source_dir.exists() or not source_dir.is_dir():
        return versions, scanned_files, parse_errors

    for workspace_dir in source_dir.iterdir():
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
                    source_updated_at, session_hash = _compute_source_version(payload)
                    versions[session_id] = {
                        "source_updated_at": source_updated_at,
                        "session_hash": session_hash,
                    }
            except (json.JSONDecodeError, OSError):
                parse_errors += 1

    return versions, scanned_files, parse_errors


def _collect_copilot_source_ids(source_dir: Path) -> Tuple[Set[str], int, int]:
    session_ids: Set[str] = set()
    scanned_files = 0
    parse_errors = 0

    if not source_dir.exists() or not source_dir.is_dir():
        return session_ids, scanned_files, parse_errors

    for workspace_dir in source_dir.iterdir():
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
                    session_ids.add(session_id)
            except (json.JSONDecodeError, OSError):
                parse_errors += 1

    return session_ids, scanned_files, parse_errors


def _collect_source_session_ids(
    scanner_name: str,
    source_dir: Path,
) -> Tuple[Set[str], int, int, bool]:
    if scanner_name == "opencode":
        ids, scanned_files, parse_errors = _collect_opencode_source_ids(source_dir)
        return ids, scanned_files, parse_errors, True
    if scanner_name == "github-copilot":
        ids, scanned_files, parse_errors = _collect_copilot_source_ids(source_dir)
        return ids, scanned_files, parse_errors, True

    return set(), 0, 0, False


def _collect_source_session_versions(
    scanner_name: str,
    source_dir: Path,
) -> Tuple[Dict[str, Dict[str, Any]], int, int, bool]:
    if scanner_name == "opencode":
        versions, scanned_files, parse_errors = _collect_opencode_source_versions(
            source_dir
        )
        return versions, scanned_files, parse_errors, True
    if scanner_name == "github-copilot":
        versions, scanned_files, parse_errors = _collect_copilot_source_versions(
            source_dir
        )
        return versions, scanned_files, parse_errors, True
    return {}, 0, 0, False


def preview_external_provider_data(
    folder_path: str,
    scanner_type: str,
    limit: int = 500,
) -> Dict[str, Any]:
    prep = _prepare_external_scanner(folder_path=folder_path, scanner_type=scanner_type)
    normalized_scanner = prep["normalized_scanner"]
    source_dir = prep["source_dir"]
    safe_limit = max(1, min(limit, 5000))
    if not prep["ok"]:
        return {
            "scanner_type": normalized_scanner,
            "folder_path": str(source_dir),
            "source_total_sessions": 0,
            "source_pending_estimate": 0,
            "source_extractable_this_run": 0,
            "scan_limit": safe_limit,
            "scan_limit_reached": False,
            "queue_pending_before_import": 0,
            "error": prep["error"],
        }

    scanner = prep["scanner"]
    source_total_sessions = scanner.count_sessions()

    db = MemoryDatabase()
    try:
        queue_pending_before_import = db.count_unprocessed_imported_sessions(
            normalized_scanner
        )

        source_versions, _, _, supported = _collect_source_session_versions(
            scanner_name=normalized_scanner,
            source_dir=source_dir,
        )
        if supported:
            source_total_sessions = len(source_versions)
            processed_known = 0
            for session_id, version in source_versions.items():
                latest = db.get_latest_processed_session(
                    agent=normalized_scanner,
                    session_id=session_id,
                    processor="default",
                )
                if _is_processed_for_source_version(
                    latest=latest,
                    source_updated_at=version.get("source_updated_at"),
                    session_hash=str(version.get("session_hash") or ""),
                ):
                    processed_known += 1
        else:
            processed_known = db.get_processed_session_count(normalized_scanner)
    finally:
        db.close()

    source_pending_estimate = max(0, source_total_sessions - processed_known)
    source_extractable_this_run = min(source_pending_estimate, safe_limit)
    scan_limit_reached = source_pending_estimate > safe_limit

    return {
        "scanner_type": normalized_scanner,
        "folder_path": str(source_dir),
        "source_total_sessions": source_total_sessions,
        "source_pending_estimate": source_pending_estimate,
        "source_extractable_this_run": source_extractable_this_run,
        "scan_limit": safe_limit,
        "scan_limit_reached": scan_limit_reached,
        "queue_pending_before_import": queue_pending_before_import,
    }


def import_external_provider_data(
    folder_path: str,
    scanner_type: str,
    limit: int = 500,
) -> Dict[str, Any]:
    preview = preview_external_provider_data(
        folder_path=folder_path,
        scanner_type=scanner_type,
        limit=limit,
    )
    normalized_scanner = preview["scanner_type"]
    source_dir = Path(preview["folder_path"])
    prep = _prepare_external_scanner(folder_path=folder_path, scanner_type=scanner_type)
    if not prep["ok"]:
        return {
            "queued": 0,
            "updated": 0,
            "imported": 0,
            "failed": 0,
            "source_total_sessions": preview.get("source_total_sessions", 0),
            "source_pending_estimate": preview.get("source_pending_estimate", 0),
            "source_extractable_this_run": preview.get(
                "source_extractable_this_run", 0
            ),
            "scan_limit": preview.get("scan_limit", max(1, min(limit, 5000))),
            "scan_limit_reached": preview.get("scan_limit_reached", False),
            "queue_pending_before_import": preview.get(
                "queue_pending_before_import", 0
            ),
            "error": prep["error"],
        }

    scanner = prep["scanner"]

    source_total_sessions = preview["source_total_sessions"]
    sessions = scanner.get_unprocessed_sessions(
        limit=preview.get("scan_limit", max(1, min(limit, 5000)))
    )
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
        "source_pending_estimate": preview.get("source_pending_estimate", 0),
        "source_extractable_this_run": preview.get("source_extractable_this_run", 0),
        "scan_limit": preview.get("scan_limit", max(1, min(limit, 5000))),
        "scan_limit_reached": preview.get("scan_limit_reached", False),
        "queue_pending_before_import": preview.get("queue_pending_before_import", 0),
        "scanner_type": normalized_scanner,
        "folder_path": str(source_dir),
        "pending_unprocessed": pending_unprocessed,
        "processed_sessions": max(0, total_imported_sessions - pending_unprocessed),
        "total_imported_sessions": total_imported_sessions,
        "errors": errors[:20],
    }


def cleanup_imported_sessions(
    scanner_type: str,
    dry_run: bool = True,
    older_than_seconds: int = 0,
    limit: int = 1000,
    confirm_token: str | None = None,
) -> Dict[str, Any]:
    """Cleanup stale/invalid imported session queue records.

    Cleanup candidates:
    - source path no longer exists
    - invalid payload JSON
    - missing/mismatched session_id in payload
    - optional age threshold exceeded
    """
    normalized_scanner = _normalize_scanner_type(scanner_type)
    safe_limit = max(1, min(limit, 5000))
    safe_older_than = max(0, older_than_seconds)

    db = MemoryDatabase()
    try:
        total_imported_before_cleanup = db.count_imported_sessions(normalized_scanner)
        queue_pending_before_cleanup = db.count_unprocessed_imported_sessions(
            normalized_scanner
        )

        rows = db.list_imported_sessions(agent=normalized_scanner, limit=safe_limit)
        now = int(time.time())
        candidates: List[Dict[str, Any]] = []
        by_reason: Dict[str, int] = {}

        for row in rows:
            reasons: List[str] = []
            source_path = row.get("source_path")
            if source_path and not Path(source_path).exists():
                reasons.append("missing_source_path")

            payload: Dict[str, Any] = {}
            payload_raw = row.get("payload")
            if payload_raw:
                try:
                    payload = json.loads(payload_raw)
                except (json.JSONDecodeError, TypeError):
                    reasons.append("invalid_payload")
            else:
                reasons.append("empty_payload")

            payload_session_id = (
                payload.get("session_id") if isinstance(payload, dict) else None
            )
            row_session_id = row.get("session_id")
            if not payload_session_id:
                reasons.append("missing_payload_session_id")
            elif payload_session_id != row_session_id:
                reasons.append("mismatched_session_id")

            imported_at = row.get("imported_at")
            if safe_older_than > 0 and isinstance(imported_at, int):
                if now - imported_at >= safe_older_than:
                    reasons.append("older_than_threshold")

            if reasons:
                for reason in set(reasons):
                    by_reason[reason] = by_reason.get(reason, 0) + 1
                candidates.append(
                    {
                        "session_id": str(row_session_id or ""),
                        "agent": str(row.get("agent") or normalized_scanner),
                        "source_scanner": str(
                            row.get("source_scanner") or normalized_scanner
                        ),
                        "imported_at": imported_at,
                        "reasons": sorted(set(reasons)),
                    }
                )

        if dry_run:
            expected_confirm_token = (
                f"confirm-imported-cleanup:{normalized_scanner}:{safe_limit}"
            )
            return {
                "dry_run": True,
                "scanner_type": normalized_scanner,
                "scanned": len(rows),
                "candidate_count": len(candidates),
                "would_delete": candidates[:200],
                "by_reason": by_reason,
                "queue_pending_before_cleanup": queue_pending_before_cleanup,
                "total_imported_before_cleanup": total_imported_before_cleanup,
                "pending_unprocessed_after": queue_pending_before_cleanup,
                "total_imported_after": total_imported_before_cleanup,
                "processed_sessions_after": max(
                    0,
                    total_imported_before_cleanup - queue_pending_before_cleanup,
                ),
                "confirm_token": expected_confirm_token,
                "summary": f"Would delete {len(candidates)} imported session records.",
            }

        expected_confirm_token = (
            f"confirm-imported-cleanup:{normalized_scanner}:{safe_limit}"
        )
        if confirm_token != expected_confirm_token:
            return {
                "dry_run": False,
                "scanner_type": normalized_scanner,
                "error": "confirm_token required for apply; run dry_run first",
                "error_code": "VALIDATION_ERROR",
                "expected_confirm_token": expected_confirm_token,
                "scanned": len(rows),
                "candidate_count": len(candidates),
                "by_reason": by_reason,
                "queue_pending_before_cleanup": queue_pending_before_cleanup,
                "total_imported_before_cleanup": total_imported_before_cleanup,
                "pending_unprocessed_after": queue_pending_before_cleanup,
                "total_imported_after": total_imported_before_cleanup,
                "processed_sessions_after": max(
                    0,
                    total_imported_before_cleanup - queue_pending_before_cleanup,
                ),
                "summary": "Cleanup apply blocked by missing/invalid confirm token.",
            }

        deleted = 0
        failed: List[Dict[str, str]] = []
        grouped: Dict[str, List[str]] = {}
        for item in candidates:
            agent = item["agent"]
            session_id = item["session_id"]
            if not session_id:
                failed.append({"session_id": "", "error": "missing_session_id"})
                continue
            grouped.setdefault(agent, []).append(session_id)

        for agent, session_ids in grouped.items():
            try:
                deleted += db.delete_imported_sessions(
                    agent=agent, session_ids=session_ids
                )
            except Exception as exc:
                for session_id in session_ids:
                    failed.append({"session_id": session_id, "error": str(exc)})

        total_imported_after = db.count_imported_sessions(normalized_scanner)
        pending_unprocessed_after = db.count_unprocessed_imported_sessions(
            normalized_scanner
        )

        return {
            "dry_run": False,
            "scanner_type": normalized_scanner,
            "scanned": len(rows),
            "candidate_count": len(candidates),
            "deleted": deleted,
            "failed": failed[:200],
            "by_reason": by_reason,
            "queue_pending_before_cleanup": queue_pending_before_cleanup,
            "total_imported_before_cleanup": total_imported_before_cleanup,
            "pending_unprocessed_after": pending_unprocessed_after,
            "total_imported_after": total_imported_after,
            "processed_sessions_after": max(
                0,
                total_imported_after - pending_unprocessed_after,
            ),
            "confirm_token": expected_confirm_token,
            "summary": f"Deleted {deleted} imported session records.",
        }
    finally:
        db.close()
