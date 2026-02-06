from fastapi.testclient import TestClient
import tempfile
from pathlib import Path

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
