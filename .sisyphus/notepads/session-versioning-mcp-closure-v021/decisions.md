
## 2026-02-07 Task: 1-2
- Keep `processed_sessions` primary key `(agent, session_id)` for backward compatibility in this iteration.
- Introduce version metadata fields (`source_updated_at`, `session_hash`, `processor`, `run_id`, `idempotency_key`) and compute conflict/noop at write time.
- MCP tool names follow existing prefix style (`gmemory_*`) to avoid breaking current tool discovery and usage patterns.

## 2026-02-08 Task: 7
- Release guard uses test-first gate: backend regression suite + frontend build must both pass before accepting scanner/import/cleanup changes.
- Rollback strategy in this iteration: deploy code rollback to previous revision while keeping additive DB schema columns (non-destructive), then rerun baseline test suite to confirm compatibility.
