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
