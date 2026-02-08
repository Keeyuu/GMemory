from fastapi.testclient import TestClient
import tempfile
from pathlib import Path
import gmemory.webapi as webapi_module

from gmemory.webapi import app
from gmemory.models import Memory
from gmemory.storage.database import MemoryDatabase


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_stats_endpoint() -> None:
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_memories" in data
    assert "processed_sessions" in data
    assert "top_hot" in data
    assert "top_cold" in data


def test_list_memories_endpoint() -> None:
    response = client.get("/api/memories", params={"limit": 5, "offset": 0})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert "has_more" in data


def test_search_endpoint() -> None:
    response = client.get("/api/search", params={"q": "test", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert "mode" in data


def test_tags_endpoint() -> None:
    response = client.get("/api/tags", params={"limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    assert "total_unique" in data


def test_memory_detail_endpoint_does_not_track_access() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test-webapi.db"

        import gmemory.config as cfg

        original_path = cfg.config._config["storage"]["db_path"]
        cfg.config._config["storage"]["db_path"] = str(db_path)

        try:
            db = MemoryDatabase()
            try:
                db.add_memory(Memory(id="web-no-track-001", content="from web api"))
            finally:
                db.close()

            local_client = TestClient(app)
            response = local_client.get("/api/memories/web-no-track-001")
            assert response.status_code == 200

            verify_db = MemoryDatabase()
            try:
                memory = verify_db.get_memory("web-no-track-001")
                assert memory is not None
                assert memory.access_count == 0
                assert memory.last_accessed_at is None
            finally:
                verify_db.close()
        finally:
            cfg.config._config["storage"]["db_path"] = original_path


def test_list_memories_supports_memory_type_filter() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test-webapi-filter.db"

        import gmemory.config as cfg

        original_path = cfg.config._config["storage"]["db_path"]
        cfg.config._config["storage"]["db_path"] = str(db_path)

        try:
            db = MemoryDatabase()
            try:
                db.add_memory(
                    Memory(
                        id="web-type-001",
                        content="pending memory",
                        preview="pending preview",
                        memory_type="pending",
                    )
                )
                db.add_memory(
                    Memory(
                        id="web-type-002",
                        content="done memory",
                        preview="done preview",
                        memory_type="done",
                    )
                )
            finally:
                db.close()

            local_client = TestClient(app)
            response = local_client.get(
                "/api/memories",
                params={"limit": 20, "offset": 0, "memory_type": "pending"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 1
            assert data["results"][0]["memory_type"] == "pending"
            assert data["results"][0]["preview"] == "pending preview"
        finally:
            cfg.config._config["storage"]["db_path"] = original_path


def test_backup_settings_endpoints() -> None:
    original_get = webapi_module.get_backup_settings
    original_update = webapi_module.update_backup_settings

    def fake_get_backup_settings() -> dict:
        return {
            "enabled": True,
            "path": "/tmp/backups",
            "max_backups": 20,
            "auto_backup_time": "02:00",
            "last_auto_backup_date": "2026-02-07",
        }

    def fake_update_backup_settings(**kwargs: object) -> dict:
        assert kwargs["enabled"] is False
        assert kwargs["path"] == "/data/backups"
        assert kwargs["max_backups"] == 15
        assert kwargs["auto_backup_time"] == "03:30"
        return {
            "updated": True,
            "settings": {
                "enabled": False,
                "path": "/data/backups",
                "max_backups": 15,
                "auto_backup_time": "03:30",
                "last_auto_backup_date": None,
            },
        }

    webapi_module.get_backup_settings = fake_get_backup_settings
    webapi_module.update_backup_settings = fake_update_backup_settings

    try:
        settings_response = client.get("/api/backup/settings")
        assert settings_response.status_code == 200
        assert settings_response.json()["max_backups"] == 20

        update_response = client.put(
            "/api/backup/settings",
            json={
                "enabled": False,
                "path": "/data/backups",
                "max_backups": 15,
                "auto_backup_time": "03:30",
            },
        )
        assert update_response.status_code == 200
        payload = update_response.json()
        assert payload["updated"] is True
        assert payload["settings"]["path"] == "/data/backups"
    finally:
        webapi_module.get_backup_settings = original_get
        webapi_module.update_backup_settings = original_update


def test_backup_list_create_restore_endpoints() -> None:
    original_list = webapi_module.list_backups
    original_create = webapi_module.create_backup
    original_restore = webapi_module.restore_backup

    def fake_list_backups(limit: int = 200) -> dict:
        assert limit == 50
        return {
            "backups": [
                {
                    "id": "backup_20260207_020000",
                    "reason": "manual",
                    "created_at": 1738893600,
                    "created_at_iso": "2026-02-07T02:00:00",
                    "path": "/tmp/backup_20260207_020000",
                    "db_file": "/tmp/backup_20260207_020000/data.db",
                    "config_file": "/tmp/backup_20260207_020000/config.json",
                    "source_db": "/tmp/data.db",
                    "size_bytes": 1024,
                }
            ],
            "total": 1,
            "path": "/tmp",
        }

    def fake_create_backup(reason: str = "manual") -> dict:
        assert reason == "manual"
        return {
            "created": True,
            "backup": {"id": "backup_20260207_020000"},
            "pruned": 0,
        }

    def fake_restore_backup(backup_id: str) -> dict:
        assert backup_id == "backup_20260207_020000"
        return {"restored": True, "backup_id": backup_id}

    webapi_module.list_backups = fake_list_backups
    webapi_module.create_backup = fake_create_backup
    webapi_module.restore_backup = fake_restore_backup

    try:
        list_response = client.get("/api/backup/list", params={"limit": 50})
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        create_response = client.post("/api/backup/create", json={"reason": "manual"})
        assert create_response.status_code == 200
        assert create_response.json()["created"] is True

        restore_response = client.post(
            "/api/backup/restore", json={"backup_id": "backup_20260207_020000"}
        )
        assert restore_response.status_code == 200
        assert restore_response.json()["restored"] is True
    finally:
        webapi_module.list_backups = original_list
        webapi_module.create_backup = original_create
        webapi_module.restore_backup = original_restore


def test_import_external_endpoint() -> None:
    original_import = webapi_module.import_external_provider_data

    def fake_import_external_provider_data(
        folder_path: str,
        scanner_type: str,
        limit: int,
    ) -> dict:
        assert folder_path == "/data/external"
        assert scanner_type == "opencode"
        assert limit == 300
        return {
            "queued": 3,
            "updated": 0,
            "imported": 3,
            "failed": 1,
            "total_sessions": 4,
            "source_total_sessions": 12,
            "scanner_type": scanner_type,
            "folder_path": folder_path,
            "pending_unprocessed": 9,
            "processed_sessions": 3,
            "total_imported_sessions": 12,
            "errors": [{"session_id": "bad-1", "error": "parse failed"}],
        }

    webapi_module.import_external_provider_data = fake_import_external_provider_data

    try:
        response = client.post(
            "/api/import/external",
            json={
                "folder_path": "/data/external",
                "scanner_type": "opencode",
                "limit": 300,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["queued"] == 3
        assert payload["pending_unprocessed"] == 9
        assert payload["failed"] == 1
    finally:
        webapi_module.import_external_provider_data = original_import


def test_preview_import_external_endpoint() -> None:
    original_preview = webapi_module.preview_external_provider_data

    def fake_preview_external_provider_data(
        folder_path: str,
        scanner_type: str,
        limit: int,
    ) -> dict:
        assert folder_path == "/data/external"
        assert scanner_type == "opencode"
        assert limit == 200
        return {
            "scanner_type": scanner_type,
            "folder_path": folder_path,
            "source_total_sessions": 120,
            "source_pending_estimate": 48,
            "source_extractable_this_run": 48,
            "scan_limit": 200,
            "scan_limit_reached": False,
            "queue_pending_before_import": 11,
        }

    webapi_module.preview_external_provider_data = fake_preview_external_provider_data

    try:
        response = client.post(
            "/api/import/external/preview",
            json={
                "folder_path": "/data/external",
                "scanner_type": "opencode",
                "limit": 200,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["source_total_sessions"] == 120
        assert payload["source_pending_estimate"] == 48
        assert payload["queue_pending_before_import"] == 11
    finally:
        webapi_module.preview_external_provider_data = original_preview


def test_cleanup_import_external_endpoint() -> None:
    original_cleanup = webapi_module.cleanup_imported_sessions

    def fake_cleanup_imported_sessions(
        scanner_type: str,
        dry_run: bool,
        older_than_seconds: int,
        limit: int,
        confirm_token: str | None,
    ) -> dict:
        assert scanner_type == "opencode"
        assert dry_run is True
        assert older_than_seconds == 3600
        assert limit == 120
        assert confirm_token is None
        return {
            "dry_run": True,
            "scanner_type": scanner_type,
            "scanned": 50,
            "candidate_count": 3,
            "would_delete": [
                {
                    "session_id": "ghost-1",
                    "agent": "opencode",
                    "source_scanner": "opencode",
                    "imported_at": 1738893600,
                    "reasons": ["missing_source_path"],
                }
            ],
            "by_reason": {"missing_source_path": 3},
            "summary": "Would delete 3 imported session records.",
        }

    webapi_module.cleanup_imported_sessions = fake_cleanup_imported_sessions

    try:
        response = client.post(
            "/api/import/external/cleanup",
            json={
                "scanner_type": "opencode",
                "dry_run": True,
                "older_than_seconds": 3600,
                "limit": 120,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["dry_run"] is True
        assert payload["candidate_count"] == 3
        assert payload["by_reason"]["missing_source_path"] == 3
    finally:
        webapi_module.cleanup_imported_sessions = original_cleanup


def test_cleanup_native_ghost_sessions_endpoint() -> None:
    original_cleanup_native = webapi_module.cleanup_native_ghost_sessions

    def fake_cleanup_native_ghost_sessions(
        scanner_type: str,
        dry_run: bool,
        limit: int,
        confirm_token: str | None,
    ) -> dict:
        assert scanner_type == "all"
        assert dry_run is False
        assert limit == 2500
        assert confirm_token == "confirm-native-cleanup:all:2500"
        return {
            "dry_run": False,
            "scanner_type": scanner_type,
            "scanned_processed_records": 120,
            "scanned_native_files": 73,
            "candidate_count": 48,
            "deleted": 48,
            "failed": [],
            "by_scanner": {"opencode": 45, "github-copilot": 3},
            "parse_errors": 0,
            "limit_reached": False,
            "details": [
                {
                    "scanner": "opencode",
                    "supported": True,
                    "native_files": 70,
                    "processed_records": 115,
                    "candidate_count": 45,
                    "parse_errors": 0,
                }
            ],
            "summary": "Deleted 48 local ghost processed-session records.",
        }

    webapi_module.cleanup_native_ghost_sessions = fake_cleanup_native_ghost_sessions

    try:
        response = client.post(
            "/api/sessions/native/ghost-cleanup",
            json={
                "scanner_type": "all",
                "dry_run": False,
                "limit": 2500,
                "confirm_token": "confirm-native-cleanup:all:2500",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["candidate_count"] == 48
        assert payload["deleted"] == 48
        assert payload["by_scanner"]["opencode"] == 45
    finally:
        webapi_module.cleanup_native_ghost_sessions = original_cleanup_native
