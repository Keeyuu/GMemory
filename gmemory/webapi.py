"""HTTP API server for GMemory web frontend."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from gmemory.commands.add import add_memory
from gmemory.commands.backup import (
    create_backup,
    get_backup_settings,
    list_backups,
    restore_backup,
    update_backup_settings,
)
from gmemory.commands.delete import delete_memory
from gmemory.commands.get import get_memories
from gmemory.commands.import_external import (
    preview_external_provider_data,
    import_external_provider_data,
    cleanup_imported_sessions,
)
from gmemory.commands.list import list_memories
from gmemory.commands.native_cleanup import cleanup_native_ghost_sessions
from gmemory.commands.quick import (
    find_by_tag,
    list_all_tags,
    recent_memories,
    today_summary,
)
from gmemory.commands.search import search_memories
from gmemory.commands.stats import get_stats
from gmemory.commands.update import update_memory
from gmemory.container import get_container


def _to_iso(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return value


def _normalize_memory_payload(memory: dict[str, Any]) -> dict[str, Any]:
    data = dict(memory)
    if "created_at" in data:
        data["created_at"] = _to_iso(data.get("created_at"))
    if "updated_at" in data:
        data["updated_at"] = _to_iso(data.get("updated_at"))
    if "last_accessed_at" in data:
        data["last_accessed_at"] = _to_iso(data.get("last_accessed_at"))
    return data


def _normalize_stats_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    top_hot = data.get("top_hot") or []
    top_cold = data.get("top_cold") or []
    data["top_hot"] = [_normalize_memory_payload(item) for item in top_hot]
    data["top_cold"] = [_normalize_memory_payload(item) for item in top_cold]
    return data


class MemoryCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    preview: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    importance: str = "medium"
    memory_type: str = "observation"
    project_path: Optional[str] = None
    project_name: Optional[str] = None


class MemoryUpdateRequest(BaseModel):
    content: str = Field(min_length=1)
    preview: str = Field(min_length=1)
    tags: Optional[list[str]] = None
    importance: Optional[str] = None
    memory_type: Optional[str] = None
    project_path: Optional[str] = None
    project_name: Optional[str] = None


class BackupCreateRequest(BaseModel):
    reason: str = "manual"


class BackupSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    path: Optional[str] = None
    max_backups: Optional[int] = Field(default=None, ge=1)
    auto_backup_time: Optional[str] = None


class BackupRestoreRequest(BaseModel):
    backup_id: str = Field(min_length=1)


class ExternalImportRequest(BaseModel):
    folder_path: str = Field(min_length=1)
    scanner_type: str = Field(min_length=1)
    limit: int = Field(default=500, ge=1, le=5000)


class ExternalCleanupRequest(BaseModel):
    scanner_type: str = Field(min_length=1)
    dry_run: bool = True
    older_than_seconds: int = Field(default=0, ge=0, le=31_536_000)
    limit: int = Field(default=1000, ge=1, le=5000)
    confirm_token: Optional[str] = None


class NativeGhostCleanupRequest(BaseModel):
    scanner_type: str = "all"
    dry_run: bool = True
    limit: int = Field(default=5000, ge=1, le=50000)
    confirm_token: Optional[str] = None


app = FastAPI(title="GMemory Web API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _reset_container_database() -> None:
    container = get_container()
    db = getattr(container, "_database", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass
    setattr(container, "_database", None)


@app.middleware("http")
async def request_db_scope(request: Any, call_next: Any) -> Any:
    _reset_container_database()
    try:
        response = await call_next(request)
        return response
    finally:
        _reset_container_database()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/stats")
async def api_stats() -> dict[str, Any]:
    return _normalize_stats_payload(get_stats())


@app.get("/api/memories")
async def api_list_memories(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    project_path: Optional[str] = None,
    importance: Optional[str] = None,
    memory_type: Optional[str] = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
) -> dict[str, Any]:
    result = list_memories(
        limit=limit,
        offset=offset,
        project_path=project_path,
        importance=importance,
        memory_type=memory_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result["results"] = [_normalize_memory_payload(item) for item in result["results"]]
    return result


@app.get("/api/memories/recent")
async def api_recent_memories(
    days: int = Query(default=7, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=200),
    project_path: Optional[str] = None,
    tags: Optional[str] = None,
) -> dict[str, Any]:
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    result = recent_memories(
        days=days,
        limit=limit,
        project_path=project_path,
        tags=tags_list,
    )
    memories = result.get("memories", [])
    normalized: list[dict[str, Any]] = []
    for item in memories:
        if hasattr(item, "id"):
            normalized.append(
                {
                    "id": item.id,
                    "content": item.content,
                    "tags": item.tags,
                    "importance": item.importance,
                    "project_path": item.project_path,
                    "project_name": item.project_name,
                    "agent": item.agent,
                    "created_at": _to_iso(item.created_at),
                    "updated_at": _to_iso(item.updated_at),
                }
            )
        else:
            normalized.append(_normalize_memory_payload(item))
    result["memories"] = normalized
    result["cutoff_timestamp"] = _to_iso(result.get("cutoff_timestamp"))
    return result


@app.get("/api/memories/{memory_id}")
async def api_get_memory(memory_id: str) -> dict[str, Any]:
    result = get_memories(ids=[memory_id], include_metadata=True, track_access=False)
    if not result["results"]:
        raise HTTPException(status_code=404, detail="Memory not found")
    return _normalize_memory_payload(result["results"][0])


@app.post("/api/memories")
async def api_create_memory(payload: MemoryCreateRequest) -> dict[str, Any]:
    result = add_memory(
        content=payload.content,
        preview=payload.preview,
        tags=payload.tags,
        importance=payload.importance,
        memory_type=payload.memory_type,
        project_path=payload.project_path,
        project_name=payload.project_name,
        require_embedding=True,
    )
    if not result.get("created"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Create failed")
        )
    created = await api_get_memory(result["id"])
    return created


@app.put("/api/memories/{memory_id}")
async def api_update_memory(
    memory_id: str, payload: MemoryUpdateRequest
) -> dict[str, Any]:
    result = update_memory(
        mem_id=memory_id,
        content=payload.content,
        preview=payload.preview,
        tags=payload.tags,
        importance=payload.importance,
        memory_type=payload.memory_type,
        project_path=payload.project_path,
        project_name=payload.project_name,
        require_embedding=True,
    )
    if not result.get("updated"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Update failed")
        )
    return await api_get_memory(memory_id)


@app.delete("/api/memories/{memory_id}")
async def api_delete_memory(memory_id: str) -> dict[str, Any]:
    try:
        result = delete_memory(memory_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/search")
async def api_search(
    q: str,
    mode: str = "hybrid",
    limit: int = Query(default=10, ge=1, le=200),
    compact: bool = True,
    project_path: Optional[str] = None,
    tags: Optional[str] = None,
    recency_weight: float = Query(default=0.0, ge=0.0, le=1.0),
    explain: bool = False,
    min_score: float = Query(default=0.2, ge=0.0, le=1.0),
) -> dict[str, Any]:
    result = search_memories(
        query=q,
        mode=mode,
        limit=limit,
        compact=compact,
        project_path=project_path,
        tags=tags,
        recency_weight=recency_weight,
        explain=explain,
        min_score=min_score,
    )
    result["results"] = [
        _normalize_memory_payload(item) for item in result.get("results", [])
    ]
    return result


@app.get("/api/today")
async def api_today() -> dict[str, Any]:
    return today_summary()


@app.get("/api/tags")
async def api_tags(limit: int = Query(default=50, ge=1, le=500)) -> dict[str, Any]:
    return list_all_tags(limit=limit)


@app.get("/api/tags/{tag}")
async def api_tag_memories(
    tag: str,
    limit: int = Query(default=20, ge=1, le=200),
    compact: bool = True,
) -> dict[str, Any]:
    result = find_by_tag(tag=tag, limit=limit, compact=compact)
    result["memories"] = [
        _normalize_memory_payload(item) for item in result.get("memories", [])
    ]
    return result


@app.get("/api/backup/settings")
async def api_backup_settings() -> dict[str, Any]:
    return get_backup_settings()


@app.put("/api/backup/settings")
async def api_backup_settings_update(payload: BackupSettingsRequest) -> dict[str, Any]:
    try:
        return update_backup_settings(
            enabled=payload.enabled,
            path=payload.path,
            max_backups=payload.max_backups,
            auto_backup_time=payload.auto_backup_time,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/backup/list")
async def api_backup_list(
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    return list_backups(limit=limit)


@app.post("/api/backup/create")
async def api_backup_create(payload: BackupCreateRequest) -> dict[str, Any]:
    result = create_backup(reason=payload.reason)
    if not result.get("created"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Backup failed")
        )
    return result


@app.post("/api/backup/restore")
async def api_backup_restore(payload: BackupRestoreRequest) -> dict[str, Any]:
    result = restore_backup(payload.backup_id)
    if not result.get("restored"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Restore failed")
        )
    return result


@app.post("/api/import/external")
async def api_import_external(payload: ExternalImportRequest) -> dict[str, Any]:
    result = import_external_provider_data(
        folder_path=payload.folder_path,
        scanner_type=payload.scanner_type,
        limit=payload.limit,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/import/external/preview")
async def api_preview_import_external(payload: ExternalImportRequest) -> dict[str, Any]:
    result = preview_external_provider_data(
        folder_path=payload.folder_path,
        scanner_type=payload.scanner_type,
        limit=payload.limit,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/import/external/cleanup")
async def api_cleanup_import_external(
    payload: ExternalCleanupRequest,
) -> dict[str, Any]:
    result = cleanup_imported_sessions(
        scanner_type=payload.scanner_type,
        dry_run=payload.dry_run,
        older_than_seconds=payload.older_than_seconds,
        limit=payload.limit,
        confirm_token=payload.confirm_token,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/sessions/native/ghost-cleanup")
async def api_cleanup_native_ghost_sessions(
    payload: NativeGhostCleanupRequest,
) -> dict[str, Any]:
    result = cleanup_native_ghost_sessions(
        scanner_type=payload.scanner_type,
        dry_run=payload.dry_run,
        limit=payload.limit,
        confirm_token=payload.confirm_token,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


def main() -> None:
    uvicorn.run("gmemory.webapi:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
