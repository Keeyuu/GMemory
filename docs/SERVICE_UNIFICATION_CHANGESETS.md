# Service Unification 可提交变更批次拆分（backend / web / docs）

> 目标：在不执行 `git commit` 的前提下，提供可直接落地的 changeset 拆分方案，支持按 `backend`、`web`、`docs` 三批提交。

## 1. 拆分原则

- **最小可回滚**：每个 batch 必须可单独 `git revert`，且不依赖“同批之外的未提交改动”才能通过最小验证。
- **跨模块依赖前置**：存在运行时依赖时，按 `Batch A (backend) -> Batch B (web) -> Batch C (docs)` 顺序提交，避免前端先落地但后端契约未稳定。
- **单批可验证**：每个 batch 必须附带可执行验证命令（测试、构建或差异核对），避免“只改代码不验收”。
- **避免混入噪音**：临时目录、草稿或与本次目标无关文件不进入 batch，防止扩大回滚面。

## 2. 提交顺序建议

1. `Batch A (backend)`
2. `Batch B (web)`
3. `Batch C (docs)`

---

## 3. Batch A（backend）

### 3.1 文件清单

```text
.github/workflows/service-smoke-gate.yml
gmemory/commands/fetch.py
gmemory/commands/workflow.py
gmemory/commands/workflow_state.py
gmemory/mcp/server.py
gmemory/mcp/tools/browse.py
gmemory/mcp/tools/workflow.py
gmemory/ports.py
gmemory/service.py
gmemory/storage/database.py
gmemory/webapi.py
install.ps1 (delete)
install.sh (delete)
pyproject.toml
tests/test_database.py
tests/test_import_external.py
tests/test_mcp.py
tests/test_service.py
tests/test_stats_command.py
tests/test_webapi.py
```

### 3.2 推荐提交消息

`feat(service): unify backend api and mcp runtime with shared workflow/state handling`

### 3.3 `git add` 示例（仅示例，不执行）

```bash
git add .github/workflows/service-smoke-gate.yml gmemory/commands/fetch.py gmemory/commands/workflow.py gmemory/commands/workflow_state.py gmemory/mcp/server.py gmemory/mcp/tools/browse.py gmemory/mcp/tools/workflow.py gmemory/ports.py gmemory/service.py gmemory/storage/database.py gmemory/webapi.py pyproject.toml tests/test_database.py tests/test_import_external.py tests/test_mcp.py tests/test_service.py tests/test_stats_command.py tests/test_webapi.py install.ps1 install.sh
```

### 3.4 验证命令（建议）

```bash
pytest tests/test_service.py tests/test_webapi.py tests/test_mcp.py tests/test_database.py tests/test_stats_command.py tests/test_import_external.py
```

---

## 4. Batch B（web）

### 4.1 文件清单

```text
web/src/components/AppSidebar.vue
web/src/composables/useMemories.ts
web/src/composables/useMcpDebug.ts
web/src/main.ts
web/src/types/memory.ts
web/src/views/Dashboard.vue
web/src/views/ExternalImport.vue (delete)
web/src/views/McpDebug.vue
web/vite.config.ts
```

### 4.2 推荐提交消息

`feat(web): adapt ui flows to unified service and add mcp debug integration`

### 4.3 `git add` 示例（仅示例，不执行）

```bash
git add web/src/components/AppSidebar.vue web/src/composables/useMemories.ts web/src/composables/useMcpDebug.ts web/src/main.ts web/src/types/memory.ts web/src/views/Dashboard.vue web/src/views/ExternalImport.vue web/src/views/McpDebug.vue web/vite.config.ts
```

### 4.4 验证命令（建议）

```bash
npm --prefix web run build
```

---

## 5. Batch C（docs）

### 5.1 文件清单

```text
docs/README_DETAILS.md
docs/SERVICE_UNIFICATION_PLAN.md
docs/SERVICE_UNIFICATION_CHANGESETS.md
opencode/agents/knowledge-archivist.md
opencode/commands/scan-memories.md
```

### 5.2 推荐提交消息

`docs(service): add unification plan and executable backend/web/docs changeset split`

### 5.3 `git add` 示例（仅示例，不执行）

```bash
git add docs/README_DETAILS.md docs/SERVICE_UNIFICATION_PLAN.md docs/SERVICE_UNIFICATION_CHANGESETS.md opencode/agents/knowledge-archivist.md opencode/commands/scan-memories.md
```

### 5.4 验证命令（建议）

```bash
git diff -- docs/README_DETAILS.md docs/SERVICE_UNIFICATION_PLAN.md docs/SERVICE_UNIFICATION_CHANGESETS.md opencode/agents/knowledge-archivist.md opencode/commands/scan-memories.md
git grep -n "service\|unification\|batch" docs/SERVICE_UNIFICATION_CHANGESETS.md docs/SERVICE_UNIFICATION_PLAN.md
```

---

## 6. 风险与回滚提示

- **风险 1（契约错位）**：若先提 `web` 后提 `backend`，可能出现前端调用新字段但服务端未上线，导致联调失败。  
  **回滚建议**：优先回滚 `Batch B`，并保持 `Batch A` 为兼容态（含 legacy wrapper / feature flag）。

- **风险 2（批次污染）**：误把临时目录或草稿纳入提交（如 `temp_repo/`、`.sisyphus/drafts/`），会增加审查与回滚成本。  
  **回滚建议**：提交前用 `git status --short` 二次核对；若已提交，单独追加 `chore` 提交移除噪音文件。

- **风险 3（删除文件影响）**：`install.ps1`、`install.sh`、`web/src/views/ExternalImport.vue` 为删除项，若外部脚本仍依赖将触发失败。  
  **回滚建议**：按需 `git revert <commit>` 恢复删除，随后在 docs 中补迁移说明。

- **风险 4（门禁覆盖不足）**：若只做局部验证，可能遗漏 API/MCP/Web 交叉回归。  
  **回滚建议**：至少按 batch 执行对应验证命令，失败即停止后续 batch 提交。

## 7. 不纳入本次三批提交（建议）

```text
temp_repo/
.sisyphus/drafts/mcp-shared-conversation-semantics.md
```

如确需纳入，请单独新增 `Batch D (misc)`，不要混入 `backend/web/docs` 主链路。
