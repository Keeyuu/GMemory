from fastapi.testclient import TestClient

from gmemory.webapi import app


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
