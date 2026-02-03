## Add Command Implementation (2026-02-03)
- Implemented `gmemory/commands/add.py`.
- Function `add_memory` allows manual memory insertion without requiring a source session ID.
- Reuses the same `Memory` model and `MemoryDatabase` as `save_memory`.
- Automatically generates embeddings for the content.
- Handles tag normalization (comma-separated string to list).
- Returns dictionary with `id` and `created` status.
- **Difference from `save_memory`**: Does not require `session_id`, does not mark any session as processed, `source_session_id` is explicitly set to `None`.

### Verification Snippet
```python
from gmemory.commands.add import add_memory

# Manually add a memory
result = add_memory(
    content="Python 3.12 introduces better error messages.",
    tags="python,update",
    importance="high",
    memory_type="fact"
)
print(f"Memory created: {result['id']}")
```

## Recovery Note (2026-02-03)
- Re-appended key learnings after detecting that earlier entries were overwritten.

## Scanner Implementation (2026-02-03)
- Implemented `OpenCodeScanner` in `gmemory/scanner/opencode.py` to scan sessions/messages/parts and filter processed sessions.
- Session metadata from `storage/session/<projectID>/ses_<sessionID>.json`; messages from `storage/message/ses_<sessionID>/msg_<messageID>.json`; parts from `storage/part/msg_<messageID>/prt_*.json`.

## Fetch Command Implementation (2026-02-03)
- Implemented `fetch_unprocessed_sessions` in `gmemory/commands/fetch.py`.
- Returns `sessions`, `has_more`, `remaining`; uses `Session.to_dict()` for JSON-ready output; `remaining` defaults to 0.

## Save/Mark Command Implementation (2026-02-03)
- Added `save_memory` in `gmemory/commands/save.py` to create Memory, embed content, insert into SQLite, and mark processed session.
- Added `mark_session` in `gmemory/commands/mark.py` to record processed sessions with timestamp.

## CLI Wiring (2026-02-03)
- Wired `fetch`, `save`, and `mark` commands in `gmemory/__main__.py` to call command modules and emit JSON.

## Search Command Implementation (2026-02-03)
- Implemented `gmemory/commands/search.py` with embedding + vector search and post-filtering for `project_path` and `tags`.
- Normalized tags input to accept both list and comma-separated string.

## Update Command Implementation (2026-02-03)
- Implemented `gmemory/commands/update.py` for granular memory updates.
- Pattern: Partial updates are handled by checking `is not None` for each argument.
- Pattern: Embedding regeneration is triggered only when `content` changes, avoiding unnecessary API calls.
- Pattern: `MemoryDatabase.update_memory` handles `updated_at` timestamp management centrally, but we also update the object in memory for consistency before saving.
- Observation: `Memory` dataclass handles tag parsing if passed as string, but the command layer also normalizes it for safety.

## Delete Command Implementation (2026-02-03)
- Implemented `gmemory/commands/delete.py` using `MemoryDatabase.delete_memory`.
- Followed pattern of checking existence before deletion to provide clear error feedback (ValueError).
- Maintained consistency with `update_memory` by using try/finally for DB resource management and returning a success dictionary.

## Command Module: Stats
- Implemented `get_stats()` in `gmemory/commands/stats.py`.
- Combines database metrics (`MemoryDatabase.get_stats()`) with scanner metrics (`OpenCodeScanner.get_unprocessed_sessions()`).
- Added group-by SQL queries for project and importance breakdowns.
- Used `try...finally` to ensure database connection is closed properly.
- Wired search/add/update/delete/stats CLI commands to their respective implementations.
- Ensured all CLI outputs are JSON-formatted and wrapped in try-except for error reporting.
- Verified function signatures for all command modules match CLI options.

## Skill Doc Note (2026-02-03)
- Added `skills/gmemory-refine/SKILL.md` with fetch -> analyze -> save/mark loop, command examples, JSON outputs, and has_more guidance.
Implemented graceful degradation for embedding service (Ollama). Used 'socket' for quick availability check instead of 'ollama' client which might block. Modified all commands to handle optional embedding and report status.

## [2026-02-04] Embedding Graceful Degradation Complete

- Added `NoOpEmbedder` in `embedder.py` that returns zero vectors when Ollama unavailable
- Added `OllamaEmbedder.is_available()` static method using socket check (200ms timeout)
- Modified `get_embedder()` factory to return `NoOpEmbedder` when Ollama not reachable
- Updated all embedding-dependent commands (add, save, update, search) to handle fallback gracefully
- Commands now return `embedding_stored: false` and `warning: Embedding service unavailable` when degraded
- Search command returns empty results with warning when embedding unavailable
- All 8 CLI commands verified working in degraded mode

## [2026-02-04] MVP Complete - Final Verification

All 11 main tasks and 5 Final Checklist items verified and marked complete:
- All commands return JSON format
- sqlite-vec creates vec_memories table with proper vector storage
- OpenCode session reading works (131 unprocessed sessions detected)
- processed_sessions mechanism working (3 sessions marked)
- Both SKILL.md files present in skills/ directory
