"""Unified HTTP service entrypoint for Web API and MCP."""

from __future__ import annotations

from contextlib import AsyncExitStack
import os
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from gmemory.mcp.server import streamable_http_app
from gmemory.webapi import app as web_app

MCP_MOUNT_PATH = "/mcp"
WEB_DIST_ENV_VAR = "GMEMORY_WEB_DIST"
_MCP_LIFESPAN_REGISTERED_KEY = "_gmemory_mcp_lifespan_registered"
_MCP_LIFESPAN_STACK_KEY = "_gmemory_mcp_lifespan_stack"
_SPA_EXCLUDED_PREFIXES = ("api", "mcp", "docs", "openapi.json")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_web_dist_path(web_dist: str | os.PathLike[str] | None = None) -> Path:
    if web_dist is None:
        web_dist = os.getenv(WEB_DIST_ENV_VAR)

    if web_dist is None:
        return _repo_root() / "web" / "dist"

    path = Path(web_dist).expanduser()
    if path.is_absolute():
        return path

    return (_repo_root() / path).resolve()


def _is_spa_fallback_excluded(path: str) -> bool:
    normalized = path.lstrip("/")
    if not normalized:
        return False

    first_segment = normalized.split("/", 1)[0]
    return first_segment in _SPA_EXCLUDED_PREFIXES


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Any) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise

            request_path = str(scope.get("path", ""))
            if _is_spa_fallback_excluded(path) or _is_spa_fallback_excluded(
                request_path
            ):
                raise

            return await super().get_response("index.html", scope)


def _get_mount(app: FastAPI, path: str) -> Mount | None:
    for route in app.routes:
        if isinstance(route, Mount) and route.path == path:
            return route
    return None


def _attach_mcp_lifespan(app: FastAPI, mcp_app: Any) -> None:
    if getattr(app.state, _MCP_LIFESPAN_REGISTERED_KEY, False):
        return

    setattr(app.state, _MCP_LIFESPAN_REGISTERED_KEY, True)

    async def _start_mcp_lifespan() -> None:
        if hasattr(app.state, _MCP_LIFESPAN_STACK_KEY):
            return

        stack = AsyncExitStack()
        await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))
        setattr(app.state, _MCP_LIFESPAN_STACK_KEY, stack)

    async def _stop_mcp_lifespan() -> None:
        stack = getattr(app.state, _MCP_LIFESPAN_STACK_KEY, None)
        if stack is None:
            return

        await stack.aclose()
        delattr(app.state, _MCP_LIFESPAN_STACK_KEY)

    app.add_event_handler("startup", _start_mcp_lifespan)
    app.add_event_handler("shutdown", _stop_mcp_lifespan)


def mount_mcp_http(app: FastAPI) -> FastAPI:
    """Mount MCP Streamable HTTP endpoint at /mcp once."""
    existing_mount = _get_mount(app, MCP_MOUNT_PATH)
    if existing_mount is not None:
        _attach_mcp_lifespan(app, existing_mount.app)
        return app

    mcp_app = streamable_http_app(path="/")
    _attach_mcp_lifespan(app, mcp_app)
    app.mount(MCP_MOUNT_PATH, mcp_app, name="gmemory-mcp")
    return app


def mount_web_ui(
    app: FastAPI, web_dist: str | os.PathLike[str] | None = None
) -> FastAPI:
    """Mount web static SPA assets at / when dist directory exists."""
    if _get_mount(app, "/") is not None:
        return app

    dist_path = _resolve_web_dist_path(web_dist)
    if not dist_path.is_dir():
        return app

    app.mount(
        "/",
        SPAStaticFiles(directory=str(dist_path), html=True, check_dir=False),
        name="gmemory-web",
    )
    return app


def create_service_app() -> FastAPI:
    return mount_web_ui(mount_mcp_http(web_app))


app = create_service_app()


def main() -> None:
    uvicorn.run("gmemory.service:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
