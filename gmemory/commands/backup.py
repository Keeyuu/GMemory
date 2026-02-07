"""Backup and restore operations for GMemory."""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from gmemory.config import config
from gmemory.container import get_container


def _expand_path(value: str) -> Path:
    return Path(os.path.expanduser(value)).resolve()


def _backup_root() -> Path:
    return _expand_path(config.lifecycle_backup_path)


def _state_file(root: Path) -> Path:
    return root / ".backup_state.json"


def _home_config_file() -> Path:
    return Path.home() / ".gmemory" / "config.json"


def _read_state(root: Path) -> Dict[str, Any]:
    state_path = _state_file(root)
    if not state_path.exists():
        return {"last_auto_backup_date": None}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"last_auto_backup_date": None}


def _write_state(root: Path, state: Dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with open(_state_file(root), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour_text, minute_text = value.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("auto_backup_time must be HH:MM in 24-hour format")
    return hour, minute


def _should_run_auto_backup(now: Optional[datetime] = None) -> bool:
    if not config.lifecycle_backup_enabled:
        return False

    current = now or datetime.now()
    root = _backup_root()
    state = _read_state(root)
    last_date = str(state.get("last_auto_backup_date") or "")
    today = current.strftime("%Y-%m-%d")
    if last_date == today:
        return False

    hour, minute = _parse_hhmm(config.lifecycle_backup_auto_time)
    scheduled = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return current >= scheduled


def run_scheduled_backup_if_due(now: Optional[datetime] = None) -> Dict[str, Any]:
    if not _should_run_auto_backup(now):
        return {"triggered": False}

    backup_result = create_backup(reason="auto")
    if backup_result.get("created"):
        root = _backup_root()
        state = _read_state(root)
        state["last_auto_backup_date"] = datetime.now().strftime("%Y-%m-%d")
        _write_state(root, state)
        return {"triggered": True, "backup": backup_result}
    return {"triggered": False, "error": backup_result.get("error")}


def _backup_manifest_path(backup_dir: Path) -> Path:
    return backup_dir / "manifest.json"


def _prune_backups(max_backups: int) -> int:
    root = _backup_root()
    if max_backups <= 0 or not root.exists():
        return 0

    dirs = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("backup_")]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    to_remove = dirs[max_backups:]
    for old_dir in to_remove:
        shutil.rmtree(old_dir, ignore_errors=True)
    return len(to_remove)


def list_backups(limit: int = 200) -> Dict[str, Any]:
    run_scheduled_backup_if_due()

    root = _backup_root()
    if not root.exists():
        return {"backups": [], "total": 0, "path": str(root)}

    items: List[Dict[str, Any]] = []
    for backup_dir in root.iterdir():
        if not backup_dir.is_dir() or not backup_dir.name.startswith("backup_"):
            continue
        manifest_path = _backup_manifest_path(backup_dir)
        if not manifest_path.exists():
            continue
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if isinstance(manifest, dict):
                items.append(manifest)
        except Exception:
            continue

    items.sort(key=lambda item: item.get("created_at", 0), reverse=True)
    if limit > 0:
        items = items[:limit]
    return {
        "backups": items,
        "total": len(items),
        "path": str(root),
    }


def create_backup(reason: str = "manual") -> Dict[str, Any]:
    root = _backup_root()
    root.mkdir(parents=True, exist_ok=True)

    db_path = config.db_path
    if not db_path.exists():
        return {"created": False, "error": f"Database file not found: {db_path}"}

    ts = int(time.time())
    stamp = datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S")
    backup_id = f"backup_{stamp}"
    backup_dir = root / backup_id
    backup_dir.mkdir(parents=True, exist_ok=False)

    target_db = backup_dir / "data.db"
    shutil.copy2(db_path, target_db)

    config_file = _home_config_file()
    config_target = backup_dir / "config.json"
    if config_file.exists():
        shutil.copy2(config_file, config_target)
    else:
        with open(config_target, "w", encoding="utf-8") as f:
            json.dump({}, f)

    manifest = {
        "id": backup_id,
        "reason": reason,
        "created_at": ts,
        "created_at_iso": datetime.fromtimestamp(ts).isoformat(),
        "path": str(backup_dir),
        "db_file": str(target_db),
        "config_file": str(config_target),
        "source_db": str(db_path),
        "size_bytes": target_db.stat().st_size,
    }
    with open(_backup_manifest_path(backup_dir), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    pruned = _prune_backups(config.lifecycle_backup_max_backups)
    return {
        "created": True,
        "backup": manifest,
        "pruned": pruned,
    }


def restore_backup(backup_id: str) -> Dict[str, Any]:
    root = _backup_root()
    backup_dir = root / backup_id
    manifest_path = _backup_manifest_path(backup_dir)
    if not manifest_path.exists():
        return {"restored": False, "error": f"Backup not found: {backup_id}"}

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    source_db = Path(str(manifest.get("db_file") or ""))
    source_config = Path(str(manifest.get("config_file") or ""))
    if not source_db.exists():
        return {"restored": False, "error": f"Backup DB file missing: {source_db}"}

    container = get_container()
    db_instance = getattr(container, "_database", None)
    if db_instance is not None:
        try:
            db_instance.close()
        except Exception:
            pass
        setattr(container, "_database", None)

    target_db = config.db_path
    target_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_db, target_db)

    target_config = _home_config_file()
    target_config.parent.mkdir(parents=True, exist_ok=True)
    if source_config.exists():
        shutil.copy2(source_config, target_config)

    config.load()
    return {
        "restored": True,
        "backup_id": backup_id,
        "database": str(target_db),
        "config": str(target_config),
    }


def get_backup_settings() -> Dict[str, Any]:
    run_scheduled_backup_if_due()
    root = _backup_root()
    state = _read_state(root)
    return {
        "enabled": config.lifecycle_backup_enabled,
        "path": str(root),
        "max_backups": config.lifecycle_backup_max_backups,
        "auto_backup_time": config.lifecycle_backup_auto_time,
        "last_auto_backup_date": state.get("last_auto_backup_date"),
    }


def update_backup_settings(
    *,
    enabled: Optional[bool] = None,
    path: Optional[str] = None,
    max_backups: Optional[int] = None,
    auto_backup_time: Optional[str] = None,
) -> Dict[str, Any]:
    backup_updates: Dict[str, Any] = {}

    if enabled is not None:
        backup_updates["enabled"] = bool(enabled)

    if path is not None:
        resolved = _expand_path(path)
        resolved.mkdir(parents=True, exist_ok=True)
        backup_updates["path"] = str(resolved)

    if max_backups is not None:
        if max_backups < 1:
            raise ValueError("max_backups must be >= 1")
        backup_updates["max_backups"] = int(max_backups)

    if auto_backup_time is not None:
        _parse_hhmm(auto_backup_time)
        backup_updates["auto_backup_time"] = auto_backup_time

    if backup_updates:
        config.persist_updates({"lifecycle": {"backup": backup_updates}})

    if "max_backups" in backup_updates:
        _prune_backups(config.lifecycle_backup_max_backups)

    return {
        "updated": True,
        "settings": get_backup_settings(),
    }
