
## 2026-02-07 Task: 1-2
- Added MCP workflow tools as `gmemory_mark_session` and `gmemory_get_processed_status` with structured error envelope and batch status semantics.
- Existing databases can fail when creating indexes on newly added columns; safe pattern is: create table if missing, then `PRAGMA table_info` + `ALTER TABLE` for missing columns before index creation.
- Versioned mark semantics can be implemented compatibly on current `(agent, session_id)` primary key using applied/noop/conflict outcomes and latest-row comparison.

## 2026-02-08 Task: 3
- Scanner skip logic should not rely on `get_processed_session(session_id, agent)` only; version compare against `get_latest_processed_session(...)` is required to avoid stale-skip.
- Stable `session_hash` can be derived from canonical JSON (`sort_keys=True`, compact separators) so content-only changes are detected even when timestamps are equal.
- A conservative fallback in `_should_reprocess` (reprocess when version metadata is missing) prevents false negatives and is safer than permanent skip for incremental pipelines.

## 2026-02-08 Task: 4
- `imported_sessions` pending calculation should run version-aware filtering in Python (`source_updated_at + session_hash`) instead of SQL `LEFT JOIN ... IS NULL` existence-only checks.
- Preview estimates are more reliable when source-side versions are computed directly from source files and compared against `get_latest_processed_session(...)` per session.
- Legacy processed markers without version metadata require explicit upgraded mark payloads in tests to keep queue semantics deterministic.

## 2026-02-08 Task: 5
- Lineage can be made deterministic by resolving active memory via `(agent, source_session_id)` and using `supersede_memory(old, new)` for changed payloads.
- Idempotent replay can be achieved by short-circuiting when active memory payload is unchanged (content/tags/importance/memory_type), returning existing `memory_id` without creating a new row.
- Default list queries should exclude superseded rows; expose explicit opt-in (`include_superseded=True`) for audit/replay tooling.

## 2026-02-08 Task: 6
- Cleanup apply paths should be two-step (`dry_run` -> `confirm_token` -> apply) to make destructive actions explicit and auditable.
- Keeping native and imported cleanup endpoints separate avoids domain bleed and makes dashboard/import metrics easier to reason about.
- Returning `before/after` counters and `by_reason` together with confirm-token validation gives both safety and observability without changing core data model.
