import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable, Tuple


REPO_ROOT = Path(__file__).resolve().parent
SRC_BASE = REPO_ROOT / "opencode"
DEST_BASE = Path.home() / ".config" / "opencode"
CONFIG_PATH = DEST_BASE / "opencode.json"


def _iter_prompt_files() -> Iterable[Tuple[Path, Path]]:
    for subdir in ("commands", "agents"):
        source_dir = SRC_BASE / subdir
        if not source_dir.exists():
            continue
        for source_file in sorted(source_dir.glob("*.md")):
            relative = source_file.relative_to(SRC_BASE)
            yield source_file, DEST_BASE / relative


def sync_prompts() -> int:
    if not SRC_BASE.exists():
        print(f"Source directory not found: {SRC_BASE}")
        return 1

    copied = 0
    for src_file, dest_file in _iter_prompt_files():
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)
        copied += 1
        print(f"synced prompt: {src_file.relative_to(SRC_BASE)}")

    print(f"prompt sync complete, files={copied}")
    return 0


def sync_opencode_config(url: str, timeout: int) -> int:
    DEST_BASE.mkdir(parents=True, exist_ok=True)

    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON in {CONFIG_PATH}: {exc}")
            return 1
    else:
        data = {}

    mcp = data.setdefault("mcp", {})
    gmemory = mcp.setdefault("gmemory", {})
    gmemory["type"] = "remote"
    gmemory["url"] = url
    gmemory["enabled"] = True
    gmemory["timeout"] = timeout

    backup = CONFIG_PATH.with_suffix(".json.bak")
    if CONFIG_PATH.exists():
        shutil.copy2(CONFIG_PATH, backup)
        print(f"backup config: {backup}")

    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"config sync complete: {CONFIG_PATH}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync repo opencode prompts to user config and optionally patch opencode.json MCP config.",
    )
    parser.add_argument(
        "--with-config",
        action="store_true",
        help="Also ensure ~/.config/opencode/opencode.json has mcp.gmemory remote config.",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8765/mcp/",
        help="Remote MCP URL for mcp.gmemory.url when --with-config is enabled.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10000,
        help="MCP timeout (ms) for mcp.gmemory.timeout when --with-config is enabled.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exit_code = sync_prompts()
    if exit_code != 0:
        return exit_code

    if args.with_config:
        return sync_opencode_config(url=args.url, timeout=args.timeout)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
