"""Unified HTTP service entrypoint for Web API and MCP."""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any

import uvicorn
from fastapi import FastAPI
from starlette.routing import Mount

from gmemory.mcp.server import streamable_http_app
from gmemory.webapi import app as web_app

MCP_MOUNT_PATH = "/mcp"
_MCP_LIFESPAN_REGISTERED_KEY = "_gmemory_mcp_lifespan_registered"
_MCP_LIFESPAN_STACK_KEY = "_gmemory_mcp_lifespan_stack"


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


app = mount_mcp_http(web_app)


def main() -> None:
    uvicorn.run("gmemory.service:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
