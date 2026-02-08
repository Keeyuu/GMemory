"""Tests for external provider session import queue behavior."""

import json
import shutil
import time
import hashlib
from pathlib import Path

import gmemory.config as cfg
from gmemory.models import ProcessedSession
from gmemory.commands.fetch import fetch_unprocessed_sessions
from gmemory.commands.import_external import (
    import_external_provider_data,
    preview_external_provider_data,
    cleanup_imported_sessions,
)
from gmemory.storage.database import MemoryDatabase
import gmemory.commands.fetch as fetch_module


def _create_opencode_session(
    base_dir: Path, session_id: str = "ext-session-001", created_at: int = 1770000000
) -> dict:
    session_dir = base_dir / "storage" / "session" / "project-1"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / f"ses_{session_id}.json"
    payload = {
        "id": session_id,
        "title": "External Session",
        "directory": "C:/external/project",
        "time": {"created": created_at},
    }
    session_file.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_external_import_queues_sessions_without_creating_memories(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "import-external.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    try:
        source_dir = tmp_path / "external-opencode"
        _create_opencode_session(source_dir, session_id="ext-session-001")

        result = import_external_provider_data(
            folder_path=str(source_dir),
            scanner_type="opencode",
            limit=100,
        )

        assert result["queued"] == 1
        assert result["updated"] == 0
        assert result["failed"] == 0
        assert result["pending_unprocessed"] == 1
        assert "source_pending_estimate" in result
        assert "source_extractable_this_run" in result
        assert "queue_pending_before_import" in result

        db = MemoryDatabase()
        try:
            # Import should queue sessions only, not create memories.
            assert db.get_stats()["memories"] == 0
            pending = db.get_unprocessed_imported_sessions(limit=10, agent="opencode")
            assert len(pending) == 1
            assert pending[0].session_id == "ext-session-001"
        finally:
            db.close()

        # Source directory can be removed after import; queued session remains processable.
        shutil.rmtree(source_dir)
        monkeypatch.setattr(
            fetch_module.ScannerRegistry,
            "list_scanners",
            classmethod(lambda cls: []),
        )

        fetched = fetch_unprocessed_sessions(limit=10, agent="all", scanner_type="all")
        assert fetched["has_more"] is False
        assert len(fetched["sessions"]) == 1
        assert fetched["sessions"][0]["session_id"] == "ext-session-001"

        # Mark processed with matching source version should remove it from pending backlog.
        db = MemoryDatabase()
        try:
            rows = db.list_imported_sessions(agent="opencode", limit=10)
            payload_raw = str(rows[0]["payload"])
            payload_obj = json.loads(payload_raw)
            payload_hash = hashlib.md5(
                json.dumps(
                    payload_obj,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            source_updated_at = int(payload_obj["started_at"])
            db.mark_session_processed(
                agent="opencode",
                session_id="ext-session-001",
                source_updated_at=source_updated_at,
                session_hash=payload_hash,
                processor="default",
            )
        finally:
            db.close()

        fetched_after = fetch_unprocessed_sessions(
            limit=10, agent="all", scanner_type="all"
        )
        assert fetched_after["sessions"] == []
    finally:
        cfg.config._config["storage"]["db_path"] = original_db_path


def test_external_import_accepts_copilot_alias(tmp_path):
    db_path = tmp_path / "import-copilot-alias.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    try:
        source_dir = tmp_path / "external-copilot"
        source_dir.mkdir(parents=True, exist_ok=True)

        result = import_external_provider_data(
            folder_path=str(source_dir),
            scanner_type="copilot",
            limit=100,
        )

        assert result["scanner_type"] == "github-copilot"
        assert result["queued"] == 0
        assert result["failed"] == 0
    finally:
        cfg.config._config["storage"]["db_path"] = original_db_path


def test_external_import_requeues_updated_session_after_processed(tmp_path):
    db_path = tmp_path / "import-requeue.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    try:
        source_dir = tmp_path / "external-opencode-requeue"
        _create_opencode_session(
            source_dir,
            session_id="ext-requeue-001",
            created_at=1770000000,
        )

        first = import_external_provider_data(
            folder_path=str(source_dir),
            scanner_type="opencode",
            limit=100,
        )
        assert first["queued"] == 1
        assert first["pending_unprocessed"] == 1

        db = MemoryDatabase()
        try:
            rows = db.list_imported_sessions(agent="opencode", limit=10)
            payload_raw = str(rows[0]["payload"])
            payload_obj = json.loads(payload_raw)
            first_hash = hashlib.md5(
                json.dumps(
                    payload_obj,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            db.mark_session_processed(
                agent="opencode",
                session_id="ext-requeue-001",
                source_updated_at=int(payload_obj["started_at"]),
                session_hash=first_hash,
                processor="default",
            )
            assert db.count_unprocessed_imported_sessions("opencode") == 0
        finally:
            db.close()

        updated_payload = {
            "id": "ext-requeue-001",
            "title": "External Session Updated",
            "directory": "C:/external/project",
            "time": {"created": 1770000100},
        }
        session_file = (
            source_dir
            / "storage"
            / "session"
            / "project-1"
            / "ses_ext-requeue-001.json"
        )
        session_file.write_text(json.dumps(updated_payload), encoding="utf-8")

        second = import_external_provider_data(
            folder_path=str(source_dir),
            scanner_type="opencode",
            limit=100,
        )
        assert second["updated"] == 1
        assert second["pending_unprocessed"] == 1
    finally:
        cfg.config._config["storage"]["db_path"] = original_db_path


def test_external_import_preview_reports_source_and_queue_counts(tmp_path):
    db_path = tmp_path / "import-preview.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    try:
        source_dir = tmp_path / "external-opencode-preview"
        payload_1 = _create_opencode_session(source_dir, session_id="ext-preview-001")
        _create_opencode_session(source_dir, session_id="ext-preview-002")
        payload_1_hash = hashlib.md5(
            json.dumps(
                payload_1,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        db = MemoryDatabase()
        try:
            db.add_processed_session(
                ProcessedSession(
                    agent="opencode",
                    session_id="ext-preview-001",
                    source_updated_at=1770000000,
                    session_hash=payload_1_hash,
                )
            )
        finally:
            db.close()

        preview = preview_external_provider_data(
            folder_path=str(source_dir),
            scanner_type="opencode",
            limit=10,
        )

        assert preview["source_total_sessions"] == 2
        assert preview["source_pending_estimate"] == 1
        assert preview["source_extractable_this_run"] == 1
        assert preview["queue_pending_before_import"] == 0
        assert preview["scan_limit_reached"] is False
    finally:
        cfg.config._config["storage"]["db_path"] = original_db_path


def test_cleanup_imported_sessions_dry_run_and_apply(tmp_path):
    db_path = tmp_path / "cleanup-imported.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    try:
        source_dir = tmp_path / "external-opencode-cleanup"
        _create_opencode_session(source_dir, session_id="ext-cleanup-001")

        imported = import_external_provider_data(
            folder_path=str(source_dir),
            scanner_type="opencode",
            limit=100,
        )
        assert imported["queued"] == 1

        # Remove source folder to create ghost queue rows.
        shutil.rmtree(source_dir)

        preview = cleanup_imported_sessions(
            scanner_type="opencode",
            dry_run=True,
            older_than_seconds=0,
            limit=100,
        )
        assert preview["dry_run"] is True
        assert preview["candidate_count"] >= 1
        assert "missing_source_path" in preview["by_reason"]

        applied = cleanup_imported_sessions(
            scanner_type="opencode",
            dry_run=False,
            older_than_seconds=0,
            limit=100,
            confirm_token=preview["confirm_token"],
        )
        assert applied["dry_run"] is False
        assert applied["deleted"] >= 1

        db = MemoryDatabase()
        try:
            remaining = db.count_imported_sessions("opencode")
            assert remaining == 0
        finally:
            db.close()
    finally:
        cfg.config._config["storage"]["db_path"] = original_db_path


def test_cleanup_imported_sessions_covers_edge_reasons(tmp_path):
    db_path = tmp_path / "cleanup-imported-edge.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    db = MemoryDatabase()
    try:
        now = int(time.time())
        existing_source = tmp_path / "existing-source"
        existing_source.mkdir(parents=True, exist_ok=True)

        with db.conn:
            db.conn.executemany(
                """
                INSERT INTO imported_sessions (
                    session_id, agent, source_scanner, source_path, payload, imported_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "edge-mismatch-001",
                        "opencode",
                        "opencode",
                        str(existing_source),
                        json.dumps({"session_id": "edge-mismatch-999"}),
                        now,
                        now,
                    ),
                    (
                        "edge-empty-001",
                        "opencode",
                        "opencode",
                        str(existing_source),
                        "",
                        now,
                        now,
                    ),
                    (
                        "edge-old-001",
                        "opencode",
                        "opencode",
                        str(existing_source),
                        json.dumps({"session_id": "edge-old-001"}),
                        now - 7200,
                        now - 7200,
                    ),
                ],
            )

        preview = cleanup_imported_sessions(
            scanner_type="opencode",
            dry_run=True,
            older_than_seconds=3600,
            limit=100,
        )
        assert preview["dry_run"] is True
        assert preview["candidate_count"] == 3
        assert preview["by_reason"]["mismatched_session_id"] >= 1
        assert preview["by_reason"]["empty_payload"] >= 1
        assert preview["by_reason"]["missing_payload_session_id"] >= 1
        assert preview["by_reason"]["older_than_threshold"] >= 1

        applied = cleanup_imported_sessions(
            scanner_type="opencode",
            dry_run=False,
            older_than_seconds=3600,
            limit=100,
            confirm_token=preview["confirm_token"],
        )
        assert applied["dry_run"] is False
        assert applied["deleted"] == 3
        assert db.count_imported_sessions("opencode") == 0
    finally:
        db.close()
        cfg.config._config["storage"]["db_path"] = original_db_path


def test_cleanup_imported_sessions_respects_batch_limit(tmp_path):
    db_path = tmp_path / "cleanup-imported-batch.db"
    original_db_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(db_path)

    db = MemoryDatabase()
    try:
        now = int(time.time())
        missing_source = tmp_path / "missing-source"

        with db.conn:
            db.conn.executemany(
                """
                INSERT INTO imported_sessions (
                    session_id, agent, source_scanner, source_path, payload, imported_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "batch-001",
                        "opencode",
                        "opencode",
                        str(missing_source),
                        json.dumps({"session_id": "batch-001"}),
                        now,
                        now,
                    ),
                    (
                        "batch-002",
                        "opencode",
                        "opencode",
                        str(missing_source),
                        json.dumps({"session_id": "batch-002"}),
                        now,
                        now,
                    ),
                    (
                        "batch-003",
                        "opencode",
                        "opencode",
                        str(missing_source),
                        json.dumps({"session_id": "batch-003"}),
                        now,
                        now,
                    ),
                ],
            )

        first_apply = cleanup_imported_sessions(
            scanner_type="opencode",
            dry_run=False,
            older_than_seconds=0,
            limit=2,
            confirm_token="confirm-imported-cleanup:opencode:2",
        )
        assert first_apply["candidate_count"] == 2
        assert first_apply["deleted"] == 2
        assert db.count_imported_sessions("opencode") == 1

        second_apply = cleanup_imported_sessions(
            scanner_type="opencode",
            dry_run=False,
            older_than_seconds=0,
            limit=2,
            confirm_token="confirm-imported-cleanup:opencode:2",
        )
        assert second_apply["candidate_count"] == 1
        assert second_apply["deleted"] == 1
        assert db.count_imported_sessions("opencode") == 0
    finally:
        db.close()
        cfg.config._config["storage"]["db_path"] = original_db_path
