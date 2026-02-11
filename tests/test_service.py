import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from starlette.routing import Mount

from gmemory.service import app, mount_mcp_http


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
