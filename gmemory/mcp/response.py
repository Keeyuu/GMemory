"""Shared MCP response helpers."""

from __future__ import annotations

import json
from typing import Any, Literal


def dumps_json(payload: Any) -> str:
    """Serialize payload for MCP tool responses."""
    return json.dumps(payload, ensure_ascii=False, default=str)


def build_error_payload(
    code: str,
    message: str,
    details: Any = None,
    legacy: Any = None,
    error_mode: Literal["object", "string"] = "object",
) -> dict[str, Any]:
    """Build a unified MCP error payload with legacy compatibility."""
    envelope: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if details is not None:
        envelope["details"] = details

    payload: dict[str, Any] = {
        "ok": False,
        "error_envelope": envelope,
    }

    if error_mode == "string":
        payload["error"] = legacy if legacy is not None else message
    else:
        if legacy is None:
            legacy_error: Any = dict(envelope)
        elif isinstance(legacy, dict):
            legacy_error = {
                "code": code,
                "message": message,
                **legacy,
            }
            if details is not None and "details" not in legacy_error:
                legacy_error["details"] = details
        else:
            legacy_error = legacy
        payload["error"] = legacy_error

    return payload


def error_json(
    code: str,
    message: str,
    details: Any = None,
    legacy: Any = None,
    error_mode: Literal["object", "string"] = "object",
) -> str:
    """Build and serialize a unified MCP error payload."""
    return dumps_json(
        build_error_payload(
            code=code,
            message=message,
            details=details,
            legacy=legacy,
            error_mode=error_mode,
        )
    )
