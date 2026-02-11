import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from starlette.routing import Mount

from gmemory.service import app, mount_mcp_http, mount_web_ui


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(
        app,
        base_url="http://127.0.0.1:8765",
        headers={
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-11-25",
        },
    ) as test_client:
        yield test_client


def test_service_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_service_docs_and_openapi_available(client: TestClient) -> None:
    docs_response = client.get("/docs")
    assert docs_response.status_code == 200

    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    assert "paths" in openapi_response.json()


def test_service_has_mcp_mount_path() -> None:
    mcp_mounts = [
        route
        for route in app.routes
        if isinstance(route, Mount) and route.path == "/mcp"
    ]
    assert len(mcp_mounts) == 1

    # Re-mount should be idempotent and keep a single /mcp mount.
    mount_mcp_http(app)
    mcp_mounts_after = [
        route
        for route in app.routes
        if isinstance(route, Mount) and route.path == "/mcp"
    ]
    assert len(mcp_mounts_after) == 1


def test_service_mcp_initialize_request(client: TestClient) -> None:
    session_id = _initialize_mcp_session(client)
    assert session_id


def test_service_mcp_minimal_flow(client: TestClient) -> None:
    session_id = _initialize_mcp_session(client)

    initialized_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    initialized_response = client.post(
        "/mcp/",
        json=initialized_payload,
        headers={"mcp-session-id": session_id},
    )
    assert initialized_response.status_code in {200, 202, 204}

    tools_list_payload = {
        "jsonrpc": "2.0",
        "id": "pytest-tools-list",
        "method": "tools/list",
        "params": {},
    }
    tools_list_response = client.post(
        "/mcp/",
        json=tools_list_payload,
        headers={"mcp-session-id": session_id},
    )

    assert tools_list_response.status_code == 200
    tools_list_payload = _decode_mcp_response_json(tools_list_response)
    tools_list_result = tools_list_payload.get("result", {})
    assert isinstance(tools_list_result, dict)
    assert "tools" in tools_list_result
    assert isinstance(tools_list_result["tools"], list)


def test_service_web_ui_root_and_spa_fallback(tmp_path: Path) -> None:
    web_dist = _prepare_web_dist(tmp_path)
    service_app = _create_test_service_app(web_dist)

    with TestClient(service_app) as test_client:
        root_response = test_client.get("/")
        assert root_response.status_code == 200
        assert "<title>GMemory UI</title>" in root_response.text

        spa_response = test_client.get("/workspace/board")
        assert spa_response.status_code == 200
        assert "<title>GMemory UI</title>" in spa_response.text


def test_service_web_ui_static_file_hit(tmp_path: Path) -> None:
    web_dist = _prepare_web_dist(tmp_path)
    service_app = _create_test_service_app(web_dist)

    with TestClient(service_app) as test_client:
        asset_response = test_client.get("/assets/app.js")
        assert asset_response.status_code == 200
        assert asset_response.text.strip() == "console.log('asset loaded');"


def test_service_web_ui_excluded_api_path_no_spa_fallback(tmp_path: Path) -> None:
    web_dist = _prepare_web_dist(tmp_path)
    service_app = _create_test_service_app(web_dist)

    with TestClient(service_app) as test_client:
        not_found_response = test_client.get("/api/missing")
        assert not_found_response.status_code == 404
        assert "GMemory UI" not in not_found_response.text


def _initialize_mcp_session(client: TestClient) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": "pytest-init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0.0.0"},
        },
    }

    response = client.post("/mcp/", json=payload)

    assert response.status_code == 200
    session_id = response.headers.get("mcp-session-id")
    assert session_id is not None
    assert '"protocolVersion"' in response.text
    return session_id


def _decode_mcp_response_json(response: Response) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()

    for line in response.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: ") :])

    pytest.fail("MCP response does not contain JSON payload")


def _prepare_web_dist(tmp_path: Path) -> Path:
    web_dist = tmp_path / "web" / "dist"
    assets_dir = web_dist / "assets"
    assets_dir.mkdir(parents=True)
    (web_dist / "index.html").write_text(
        "<!doctype html><html><head><title>GMemory UI</title></head>"
        "<body><div id='app'></div></body></html>",
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text(
        "console.log('asset loaded');\n", encoding="utf-8"
    )
    return web_dist


def _create_test_service_app(web_dist: Path) -> FastAPI:
    service_app = FastAPI()

    @service_app.get("/api/health")
    async def _health() -> dict[str, str]:
        return {"status": "ok"}

    mount_web_ui(service_app, web_dist=web_dist)
    return service_app
