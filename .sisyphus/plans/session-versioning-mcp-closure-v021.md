# GMemory Session Versioning & MCP Closure Plan

## TL;DR

> **Quick Summary**: 建立 GMemory 的版本化会话处理闭环，确保同一 `session_id` 更新后可正确重处理，并通过 MCP 标准工具实现可追溯的 `mark/check status` 工作流。
>
> **Deliverables**:
> - 新增 MCP 工具：`mark_session`、`get_processed_status`（含幂等与冲突语义）
> - processed 状态版本语义：`source_updated_at + session_hash`
> - 扫描判定升级：文件层粗筛 + 会话层精判
> - imported queue 重入规则与 cleanup 安全护栏
> - 测试矩阵与可观测指标
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 2 -> Task 3 -> Task 5 -> Task 7

---

## Context

### Original Request
- 用户要求：先让架构师评审，再把“同会话更新重处理 + MCP 闭环 + Queue/Ghost 清理治理”规划清楚。
- 用户已确认采用推荐方向：**append new memory + supersede old memory**。

### Interview Summary
**Key Discussions**:
- 现状 `processed_sessions` 仅按 `(agent, session_id)` 标记，缺版本语义，更新会话可能被误跳过。
- `ScanStateManager` 目前是文件级增量状态（`size/mtime/content_hash`），与 processed 状态缺少强绑定。
- cleanup 能力已存在，但自动化和保留策略不统一，长期运行有 ghost/pending 漂移风险。

**Research Findings**:
- `gmemory/scanner/opencode.py`、`gmemory/scanner/copilot.py` 存在“先 state 跳过再 processed 判断”路径，可能掩盖更新。
- `gmemory/storage/database.py` 的 `processed_sessions` 缺少会话版本字段，无法表达“旧版已处理 vs 新版待处理”。
- Oracle 评审结论：Approve with conditions，必须先补版本语义、幂等冲突模型、批量状态查询。

### Metis Review
**Identified Gaps** (addressed):
- Metis 调用返回空文本，未产出新增问题清单。
- 已用本地代码证据 + Oracle 评审补齐守护条件：
  - 以 `source_updated_at + session_hash` 作为版本真相源
  - `mark_session` 必须有 `idempotency_key` 与 `CONFLICT` 语义
  - cleanup 默认 `dry_run` + confirm token + 限流 + 审计记录

---

## Work Objectives

### Core Objective
- 构建可验证、可回放、可并发安全的会话处理闭环：当会话更新时自动进入重处理路径；当会话未更新时保持幂等跳过。

### Concrete Deliverables
- MCP: `mark_session`, `get_processed_status`（含 batch）
- DB/模型：processed 状态版本字段与查询索引
- Scanner: 版本感知的重处理判定
- Import queue: 基于版本变化的重入语义
- Memory lineage: append + supersede 策略
- Cleanup policy: native/imported 分域治理 + 安全护栏

### Definition of Done
- [x] 同一 `session_id` 内容更新后，重扫描可稳定进入重处理（可自动验证）
- [x] 同版本重复处理不会重复落库（幂等）
- [x] 旧版本写入不会覆盖新版本（冲突保护）
- [x] imported 更新会话可重新进入 pending
- [x] cleanup 执行满足 dry-run/confirm/limit 安全约束

### Must Have
- 版本真相源：`source_updated_at + session_hash`
- 明确状态机：`pending -> processing -> processed|failed|skipped|closed`
- MCP 可变工具标准化错误模型与幂等语义
- append + supersede 记忆谱系

### Must NOT Have (Guardrails)
- 不允许仅以 `(agent, session_id)` 判定“永远已处理”
- 不允许 native cleanup 与 external import cleanup 混域
- 不允许无 `dry_run` 预览的直接批量删除
- 不允许“先 mark 后写 memory”
- 不允许 acceptance criteria 依赖人工点击/人工判断

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> 所有任务验收必须由 agent 自动执行完成，禁止人工操作作为验收步骤。

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: YES (Tests-after)
- **Framework**: `pytest` + 前端 `npm build` + Playwright 场景

### Agent-Executed QA Scenarios (Global Rules)
- 每个任务至少 1 个 happy path + 1 个 negative/conflict path。
- 证据输出统一到 `.sisyphus/evidence/`。
- API 验证使用 `curl` + JSON 字段断言。
- UI 验证使用 Playwright，必须带精确 selector 与截图路径。

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Start Immediately):
- Task 1: MCP Contract & Tool Surface
- Task 2: Versioned Processed-State Model

Wave 2 (After Wave 1):
- Task 3: Scanner Reprocess Semantics
- Task 4: Imported Queue Re-entry Semantics
- Task 6: Cleanup Safety Rails

Wave 3 (After Wave 2):
- Task 5: Memory Lineage (Append + Supersede)

Wave 4 (After Wave 3):
- Task 7: Integration, Tests, Observability, Release Guard

Critical Path: Task 2 -> Task 3 -> Task 5 -> Task 7
Parallel Speedup: ~35-45% faster than strict sequential

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|----------------------|
| 1 | None | 3, 7 | 2 |
| 2 | None | 3, 4, 5, 6, 7 | 1 |
| 3 | 1, 2 | 5, 7 | 4, 6 |
| 4 | 2 | 7 | 3, 6 |
| 5 | 2, 3 | 7 | None |
| 6 | 2 | 7 | 3, 4 |
| 7 | 1,2,3,4,5,6 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|--------------------|
| 1 | 1, 2 | `delegate_task(category="unspecified-high", load_skills=["mcp-builder","backend-patterns"], run_in_background=false)` |
| 2 | 3, 4, 6 | scanner/import/cleanup 分任务并发派发 |
| 3 | 5 | 单任务串行，避免 lineage 并发冲突 |
| 4 | 7 | 集成验证任务，串行执行并产证据 |

---

## TODOs

- [x] 1. MCP Contract and Tool Registration

  **What to do**:
  - 定义 `mark_session` 与 `get_processed_status` 的 request/response schema。
  - 增加 batch 查询能力与错误模型（`VALIDATION_ERROR`, `CONFLICT`, `INTERNAL`）。
  - 在 MCP server 注册并暴露工具，保持命名与现有风格一致。

  **Must NOT do**:
  - 不要在无幂等键下实现可变写接口。
  - 不要返回非结构化错误字符串作为唯一错误信息。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 涉及协议设计 + 服务集成，错误代价高。
  - **Skills**: `mcp-builder`, `backend-patterns`
    - `mcp-builder`: MCP 工具契约、错误模型、注解规范。
    - `backend-patterns`: API 语义一致性与状态转换设计。
  - **Skills Evaluated but Omitted**:
    - `frontend-design`: 与本任务无关。

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: 3, 7
  - **Blocked By**: None

  **References**:
  - `gmemory/mcp/server.py` - MCP server capability registration入口。
  - `gmemory/mcp/tools/stats.py` - 现有工具返回结构样式参考。
  - `gmemory/mcp/tools/crud.py` - MCP 参数/返回风格参考。
  - `gmemory/commands/mark.py` - 现有 mark 语义来源。
  - `gmemory/ports.py` - 状态接口抽象边界。
  - `https://modelcontextprotocol.io/legacy/concepts/tools` - 官方 tools 设计原则。

  **Acceptance Criteria**:
  - [x] `mark_session` 支持 `idempotency_key` 且重复调用返回 `noop|applied` 明确结果。
  - [x] `get_processed_status` 支持 batch，返回 `needs_reprocess` 计算字段。
  - [x] 冲突场景返回 `CONFLICT` 且包含 `current_latest`。

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: mark_session idempotency
    Tool: Bash (pytest)
    Preconditions: test DB isolated
    Steps:
      1. Run targeted MCP tool tests for mark_session duplicate requests
      2. Assert second call result is noop and same latest state
    Expected Result: No duplicate state rows
    Evidence: .sisyphus/evidence/task-1-idempotency.txt

  Scenario: mark_session stale version conflict
    Tool: Bash (pytest)
    Preconditions: newer version already marked
    Steps:
      1. Call mark_session with older source_updated_at/session_hash
      2. Assert code == CONFLICT
      3. Assert response contains current_latest
    Expected Result: stale write rejected
    Evidence: .sisyphus/evidence/task-1-conflict.txt
  ```

  **Commit**: YES
  - Message: `feat(mcp): add version-aware session status tools`
  - Files: `gmemory/mcp/server.py`, `gmemory/mcp/tools/*`, tests
  - Pre-commit: `uv run pytest tests/test_mcp.py`

---

- [x] 2. Versioned Processed-State Data Model

  **What to do**:
  - 为 processed 状态引入版本字段：`source_updated_at`, `session_hash`, `processor`, `run_id`, `idempotency_key`。
  - 添加必要索引/唯一约束以支持 latest 查询和幂等写。
  - 更新 database 方法与 ports 契约。

  **Must NOT do**:
  - 不要破坏现有 `(agent, session_id)` 基础兼容性。
  - 不要把 schema 变更与业务语义变更混在同一不可回滚步骤。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 数据模型演进涉及迁移风险。
  - **Skills**: `backend-patterns`, `coding-standards`
    - `backend-patterns`: schema/索引/迁移策略。
    - `coding-standards`: 向后兼容与错误处理一致性。
  - **Skills Evaluated but Omitted**:
    - `mcp-builder`: 本任务以存储层为主。

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: 3,4,5,6,7
  - **Blocked By**: None

  **References**:
  - `gmemory/storage/database.py` - `processed_sessions` 表与相关读写函数。
  - `gmemory/storage/migrations.py` - 迁移版本管理入口。
  - `gmemory/models.py` - ProcessedSession 数据结构。
  - `gmemory/ports.py` - 接口定义需要同步。
  - `tests/test_database.py` - DB 行为验证模式。

  **Acceptance Criteria**:
  - [x] migration 可在已有数据库上安全执行，旧功能不回归。
  - [x] 同 `(processor, agent, session_id, idempotency_key)` 重复写入不重复落库。
  - [x] latest 状态查询能基于版本字段稳定返回。

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: migration backward compatibility
    Tool: Bash (pytest)
    Preconditions: fixture with pre-migration DB
    Steps:
      1. Run migration
      2. Execute existing processed-session read/write tests
      3. Execute new version-field tests
    Expected Result: all pass
    Evidence: .sisyphus/evidence/task-2-migration.txt

  Scenario: duplicate idempotency key write
    Tool: Bash (pytest)
    Preconditions: same request replayed twice
    Steps:
      1. Insert mark row via command/db API
      2. Replay same payload
      3. Query row count
    Expected Result: row count unchanged
    Evidence: .sisyphus/evidence/task-2-idempotency-db.txt
  ```

  **Commit**: YES
  - Message: `feat(storage): version-aware processed session schema`
  - Files: `gmemory/storage/database.py`, `gmemory/storage/migrations.py`, tests
  - Pre-commit: `uv run pytest tests/test_database.py`

---

- [x] 3. Scanner Reprocess Semantics (Coarse + Precise)

  **What to do**:
  - 调整 `opencode/copilot` 扫描顺序：文件层仅做粗筛，不得直接终判。
  - 对候选会话计算 `session_hash`，与 latest processed 版本比较。
  - 规则：`source_updated_at` 变大或 `session_hash` 变化 -> reprocess。

  **Must NOT do**:
  - 不要继续依赖“`session_id` 命中即永远 skip”。
  - 不要只依赖大文件采样 hash 作为终判依据。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 扫描路径是数据正确性核心。
  - **Skills**: `backend-patterns`, `coding-standards`
    - `backend-patterns`: 增量处理判定逻辑。
    - `coding-standards`: 回归风险控制。
  - **Skills Evaluated but Omitted**:
    - `mcp-builder`: 此任务非 MCP 接口层。

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4,6)
  - **Blocks**: 5,7
  - **Blocked By**: 1,2

  **References**:
  - `gmemory/scanner/state.py` - 文件级增量状态与 hash 逻辑。
  - `gmemory/scanner/opencode.py` - 当前 skip 路径与 processed 判断。
  - `gmemory/scanner/copilot.py` - 同类扫描器需要同步。
  - `gmemory/commands/fetch.py` - scanner 结果汇聚入口。
  - `tests/test_scanner_opencode.py` - 扫描行为回归测试基线。

  **Acceptance Criteria**:
  - [x] 文件未变且会话版本未变 -> 不重处理。
  - [x] 同一 session 内容变更 -> 重处理。
  - [x] stale processed 状态不再导致误跳过。

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: unchanged session remains skipped
    Tool: Bash (pytest)
    Preconditions: baseline scan already marked processed
    Steps:
      1. Re-run scanner with same source files
      2. Assert returned unprocessed list excludes session
    Expected Result: no duplicate processing
    Evidence: .sisyphus/evidence/task-3-unchanged.txt

  Scenario: same session_id updated should reappear
    Tool: Bash (pytest)
    Preconditions: processed row exists for older version
    Steps:
      1. Mutate session payload (same session_id, changed content)
      2. Re-run scanner/fetch
      3. Assert session appears in unprocessed list
    Expected Result: reprocess candidate detected
    Evidence: .sisyphus/evidence/task-3-updated-reprocess.txt
  ```

  **Commit**: YES
  - Message: `fix(scanner): reprocess updated sessions by version`
  - Files: `gmemory/scanner/*.py`, related tests
  - Pre-commit: `uv run pytest tests/test_scanner_opencode.py`

---

- [x] 4. Imported Queue Re-entry Semantics

  **What to do**:
  - 更新 imported pending 判定：源版本变更时可重入 pending。
  - 规则优先：`source_updated_at/session_hash`，时间比较仅兜底。
  - 保持 Import 页指标语义清晰（source vs queue）。

  **Must NOT do**:
  - 不要把 imported pending 继续等价为 “processed 表中有 session_id 就排除”。
  - 不要混入 native cleanup 逻辑。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 队列语义影响 backlog 正确性。
  - **Skills**: `backend-patterns`, `vue-best-practices`
    - `backend-patterns`: SQL/命令语义修订。
    - `vue-best-practices`: 前端指标呈现同步。
  - **Skills Evaluated but Omitted**:
    - `frontend-design`: 不是视觉重构任务。

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3,6)
  - **Blocks**: 7
  - **Blocked By**: 2

  **References**:
  - `gmemory/commands/import_external.py` - preview/import/cleanup 语义实现。
  - `gmemory/storage/database.py` - imported + processed join 查询。
  - `gmemory/webapi.py` - import/preview/cleanup API。
  - `web/src/views/ExternalImport.vue` - 指标显示与操作流程。
  - `tests/test_import_external.py` - 当前导入行为测试。

  **Acceptance Criteria**:
  - [x] imported 会话更新后重新进入 pending。
  - [x] preview 与 import 计数语义一致。
  - [x] Import 页面不再出现“看起来已处理但 pending 不变”假象。

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: updated imported session re-enters queue
    Tool: Bash (pytest)
    Preconditions: imported row exists and was previously processed
    Steps:
      1. Update imported payload version/hash
      2. Query unprocessed imported sessions
      3. Assert session is returned
    Expected Result: queue re-entry works
    Evidence: .sisyphus/evidence/task-4-reentry.txt

  Scenario: import page metrics consistency
    Tool: Playwright (playwright skill)
    Preconditions: local web + api running
    Steps:
      1. Navigate to /import
      2. Trigger Preview Scan
      3. Trigger Start Import
      4. Assert source metrics and queue metrics sections show distinct semantics
      5. Screenshot .sisyphus/evidence/task-4-import-metrics.png
    Expected Result: no mixed/contradictory counts
    Evidence: .sisyphus/evidence/task-4-import-metrics.png
  ```

  **Commit**: YES
  - Message: `fix(import): re-enter updated sessions into pending queue`
  - Files: `gmemory/commands/import_external.py`, `gmemory/storage/database.py`, web/tests
  - Pre-commit: `uv run pytest tests/test_import_external.py tests/test_webapi.py`

---

- [x] 5. Memory Lineage: Append + Supersede

  **What to do**:
  - 更新会话重处理时，追加新 memory 并建立 supersede 关系。
  - 确保查询默认返回最新有效版本，历史可追溯。
  - 处理去重与重复 supersede 防护。

  **Must NOT do**:
  - 不要原地覆盖旧 memory 内容。
  - 不要生成断裂 lineage（新旧关系不一致）。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 影响长期数据质量与审计能力。
  - **Skills**: `backend-patterns`, `coding-standards`
    - `backend-patterns`: 版本谱系与查询策略。
    - `coding-standards`: 数据一致性和迁移安全。
  - **Skills Evaluated but Omitted**:
    - `mcp-builder`: 主要是 memory 层。

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (Sequential)
  - **Blocks**: 7
  - **Blocked By**: 2,3

  **References**:
  - `gmemory/commands/save.py` - save 后 mark 路径。
  - `gmemory/storage/database.py` - memory 更新/查询逻辑。
  - `gmemory/commands/search.py` - 结果过滤与排序语义。
  - `gmemory/models.py` - Memory 字段定义。

  **Acceptance Criteria**:
  - [x] 更新会话产生新 memory，并标记旧 memory 被 superseded。
  - [x] 默认查询不返回过时版本（除非显式 include）。
  - [x] lineage 可被 session/detail/report 路径追踪。

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: append+supersede on reprocess
    Tool: Bash (pytest)
    Preconditions: initial memory exists for session
    Steps:
      1. Reprocess updated session
      2. Assert new memory row created
      3. Assert old memory superseded_by points to new memory
    Expected Result: lineage valid and query returns latest
    Evidence: .sisyphus/evidence/task-5-lineage.txt

  Scenario: duplicate replay does not create extra lineage
    Tool: Bash (pytest)
    Preconditions: same version replay
    Steps:
      1. Replay same version processing
      2. Assert no additional memory row
    Expected Result: idempotent lineage behavior
    Evidence: .sisyphus/evidence/task-5-idempotent-lineage.txt
  ```

  **Commit**: YES
  - Message: `feat(memory): append and supersede on session updates`
  - Files: `gmemory/commands/save.py`, `gmemory/storage/database.py`, tests
  - Pre-commit: `uv run pytest tests/test_workflow.py tests/test_search.py`

---

- [x] 6. Cleanup Policy & Safety Rails

  **What to do**:
  - 标准化 cleanup 执行策略：`dry_run` 默认、confirm token、`max_rows` 限流。
  - 分域治理：Dashboard(native) 与 Import(external) 彻底隔离。
  - 增加 cleanup 审计返回字段（before/after counts, deleted_by_reason）。

  **Must NOT do**:
  - 不要允许无确认直接 destructive cleanup。
  - 不要在首页触发 external queue 清理。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 涉及删除动作与运维安全。
  - **Skills**: `backend-patterns`, `vue-best-practices`
    - `backend-patterns`: API 安全护栏与参数校验。
    - `vue-best-practices`: UI 确认交互与状态同步。
  - **Skills Evaluated but Omitted**:
    - `frontend-design`: 不涉及视觉风格改版。

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3,4)
  - **Blocks**: 7
  - **Blocked By**: 2

  **References**:
  - `gmemory/commands/native_cleanup.py` - native ghost 清理逻辑。
  - `gmemory/commands/import_external.py` - external cleanup 逻辑。
  - `gmemory/webapi.py` - cleanup 路由和请求模型。
  - `web/src/views/Dashboard.vue` - native cleanup 交互。
  - `web/src/views/ExternalImport.vue` - external cleanup 交互。
  - `tests/test_native_cleanup.py`, `tests/test_webapi.py` - 现有覆盖基础。

  **Acceptance Criteria**:
  - [x] cleanup API 默认 dry-run。
  - [x] apply 必须带 confirm token，缺失返回 validation error。
  - [x] UI 分域清理不串线，pending 计数可正确下降。

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: cleanup apply without token rejected
    Tool: Bash (curl)
    Preconditions: API running
    Steps:
      1. POST cleanup apply payload without confirm token
      2. Assert status 4xx and error code validation
    Expected Result: destructive action blocked
    Evidence: .sisyphus/evidence/task-6-token-required.json

  Scenario: dashboard native cleanup updates stats
    Tool: Playwright (playwright skill)
    Preconditions: web/api running with test data
    Steps:
      1. Navigate /dashboard
      2. Trigger Native Cleanup confirm flow
      3. Assert pending number decreases after refresh
      4. Screenshot .sisyphus/evidence/task-6-dashboard-cleanup.png
    Expected Result: native pending drops and UI syncs
    Evidence: .sisyphus/evidence/task-6-dashboard-cleanup.png
  ```

  **Commit**: YES
  - Message: `feat(cleanup): add safety rails and strict domain separation`
  - Files: cleanup commands, `webapi.py`, dashboard/import views, tests
  - Pre-commit: `uv run pytest tests/test_native_cleanup.py tests/test_webapi.py`

---

- [x] 7. Integration Verification, Observability, and Release Guard

  **What to do**:
  - 增加闭环指标：`reprocess_rate`, `hash_mismatch_rate`, `ghost_count`, `cleanup_deleted_rows`。
  - 完成端到端回归：MCP -> scanner -> save/mark -> stats -> cleanup。
  - 形成发布门禁检查清单与回滚策略。

  **Must NOT do**:
  - 不要只验证单模块而跳过全链路。
  - 不要在缺少证据文件时宣称通过。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 最终集成质量门禁。
  - **Skills**: `backend-patterns`, `webapp-testing`
    - `backend-patterns`: 链路指标与日志结构。
    - `webapp-testing`: 浏览器与接口联调验证。
  - **Skills Evaluated but Omitted**:
    - `frontend-design`: 非设计任务。

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (final integration)
  - **Blocks**: None
  - **Blocked By**: 1,2,3,4,5,6

  **References**:
  - `gmemory/commands/stats.py` - 指标输出聚合。
  - `gmemory/webapi.py` - stats/API 输出。
  - `web/src/components/AppSidebar.vue` - 跨页面 stats 同步点。
  - `web/src/composables/useMemories.ts` - 共享状态刷新路径。
  - `tests/test_stats_command.py` - stats 回归测试。

  **Acceptance Criteria**:
  - [x] 全链路测试通过并产出证据。
  - [x] 关键指标在更新/清理场景下变化符合预期。
  - [x] 回滚步骤可执行（migration rollback 或 feature flag fallback）。

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: full loop reprocess and status verification
    Tool: Bash (pytest + curl)
    Preconditions: seeded fixtures for updated session
    Steps:
      1. Execute pipeline test: fetch -> process -> mark -> status check
      2. Assert needs_reprocess=no for latest version
      3. Update source session and rerun
      4. Assert needs_reprocess=yes then processed to no
    Expected Result: closed loop deterministic
    Evidence: .sisyphus/evidence/task-7-full-loop.txt

  Scenario: UI stats consistency after cleanup/import
    Tool: Playwright (playwright skill)
    Preconditions: web/api running
    Steps:
      1. Perform import and cleanup actions
      2. Navigate dashboard and sidebar
      3. Assert displayed pending counts are consistent
      4. Screenshot .sisyphus/evidence/task-7-stats-consistency.png
    Expected Result: no stale mismatch across components
    Evidence: .sisyphus/evidence/task-7-stats-consistency.png
  ```

  **Commit**: YES
  - Message: `chore(verification): add full-loop tests and observability guards`
  - Files: stats/api/web/tests related files
  - Pre-commit: `uv run pytest` and `npm run build`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(mcp): add version-aware session status tools` | mcp server/tools + tests | `uv run pytest tests/test_mcp.py` |
| 2 | `feat(storage): version-aware processed session schema` | database/migrations/models/tests | `uv run pytest tests/test_database.py` |
| 3 | `fix(scanner): reprocess updated sessions by version` | scanners/fetch/tests | `uv run pytest tests/test_scanner_opencode.py` |
| 4 | `fix(import): re-enter updated sessions into pending queue` | import cmd/db/web/tests | `uv run pytest tests/test_import_external.py tests/test_webapi.py` |
| 5 | `feat(memory): append and supersede on session updates` | save/db/search/tests | `uv run pytest tests/test_workflow.py tests/test_search.py` |
| 6 | `feat(cleanup): add safety rails and strict domain separation` | cleanup cmd/api/web/tests | `uv run pytest tests/test_native_cleanup.py tests/test_webapi.py` |
| 7 | `chore(verification): add full-loop tests and observability guards` | stats/web/tests | `uv run pytest && npm run build` |

---

## Success Criteria

### Verification Commands
```bash
uv run pytest tests/test_mcp.py tests/test_database.py tests/test_scanner_opencode.py tests/test_import_external.py tests/test_native_cleanup.py tests/test_stats_command.py
# Expected: all pass

npm run build
# Expected: build success, 0 fatal errors

uv run python -m py_compile gmemory/commands/import_external.py gmemory/commands/native_cleanup.py gmemory/webapi.py
# Expected: no syntax errors
```

### Final Checklist
- [x] 所有 Must Have 已实现
- [x] 所有 Must NOT Have 未触发
- [x] append+supersede 路径可追溯
- [x] MCP mark/status 闭环可自动验收
- [x] cleanup 安全护栏生效
- [x] pending 计数在更新/清理后可正确变化
