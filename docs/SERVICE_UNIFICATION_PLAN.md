# backend API + MCP 单服务合并工程计划

## 1. 背景

当前 `gmemory-web`（HTTP API）与 `gmemory-mcp`（MCP stdio server）以双入口运行，存在以下问题：

- 运行形态分离：部署、监控、版本回滚需要双份流程，故障定位链路长。
- 行为不一致：同一业务能力在 Web/API 与 MCP 侧可能出现 error、schema、timeout 策略漂移。
- 联调成本高：Web 开发与 MCP 调试环境并行维护，缺少统一门禁与证据标准。
- 运维复杂度高：日志、trace、配置项分散，不利于统一 SLO 与问题复盘。

## 2. 目标

- 当前目标态（current target state）为 `gmemory-service` single-process runtime。
- 将 backend API 与 MCP 运行时合并为单进程服务入口（暂定 `gmemory-service`）。
- 统一业务层、错误模型、输入输出 schema 与 observability 约束。
- 建立 Web 对接联调门禁（本地 + CI），确保服务升级可验证、可回滚。
- 保持现有 `gmemory-web` / `gmemory-mcp` 命令兼容（迁移期保留）。

## 3. 非目标

- 不在本计划内重写核心存储引擎（SQLite / sqlite-vec / FTS）。
- 不在本计划内调整记忆业务语义（search/profile/CRUD/workflow 语义保持一致）。
- 不在本计划内引入跨服务分布式架构（本阶段仍为单机 Local-First）。
- 不强制一次性移除旧命令；仅在 deprecation policy 生效后分阶段下线。

## 4. 架构目标图（文字版）

```text
[Web Frontend / CLI / MCP Client]
            |
            v
      +-----------------------+
      |    gmemory-service    |
      |-----------------------|
      | API Router (HTTP)     |
      | MCP Adapter (tools)   |
      | Shared Service Layer  |
      | Validation/Schema     |
      | Error Mapper          |
      | Logging/Tracing       |
      +-----------------------+
            |
            v
   +----------------------------+
   | Storage (SQLite/FTS/Vec)   |
   +----------------------------+
```

关键原则：

- API 与 MCP 仅作为“协议适配层”，核心逻辑收敛到 `Shared Service Layer`。
- 统一 schema 与 error contract，避免双协议下返回结构漂移。
- 统一 `request_id` / `trace_id` / `session_id` 贯穿日志与排障。

## 5. Phase 0~3 计划

### Phase 0 - Baseline 与契约冻结

**输入**

- 现有 `gmemory/webapi.py` 与 `gmemory/mcp/*` 能力清单。
- 当前 Web 联调路径与常见命令（`gmemory-web`、`gmemory-mcp`）。
- 现有错误场景与排障经验。

**输出**

- 能力矩阵：API endpoint ↔ MCP tool 映射表。
- 契约基线：error model、schema 字段、timeout/retry 默认值草案。
- 联调门禁草案：本地步骤 + CI 阈值。

**风险**

- 基线不完整导致后续迁移漏项。
- 隐式依赖（前端或脚本侧）未被识别。

**回滚点**

- 保持现有双入口运行，不改动 runtime 默认行为。

**验收标准**

- 完成“能力映射 + 契约冻结”文档评审。
- 关键路径（search/add/update/session workflow）均有映射与 owner。

### Phase 1 - Service Skeleton 与双协议接入

**输入**

- Phase 0 契约基线。
- 当前 API/MCP 启动脚本与依赖清单。

**输出**

- 新增统一入口 `gmemory-service`（单进程承载 API + MCP adapter）。
- 旧入口保留为 compatibility wrapper（内部调用新 service 或共享 bootstrap）。
- 统一配置层（port、log level、timeout、feature flags）。

**风险**

- 启动顺序或生命周期管理不当，导致某协议不可用。
- 资源竞争（线程/事件循环/stdio）导致稳定性波动。

**回滚点**

- feature flag 关闭 unified mode，恢复旧入口独立运行。

**验收标准**

- 本地可通过单命令同时提供 API 能力与 MCP tool 能力。
- 旧命令仍可启动且行为兼容（输出包含迁移提示）。

### Phase 2 - 语义统一与门禁接入

**输入**

- Phase 1 服务骨架与兼容层。
- Web 联调脚本、构建脚本与基础测试能力。

**输出**

- 统一 error model 与 schema version 标识。
- timeout/retry/idempotency 策略在 API/MCP 同步生效。
- CI 引入联调门禁（后文详述），失败即阻断合并。

**风险**

- 历史调用方依赖旧错误字段，触发兼容问题。
- 门禁过严导致研发效率下降。

**回滚点**

- 按 feature flag 仅启用核心路径统一，其余路径暂回 legacy adapter。

**验收标准**

- Web 关键页面联调通过（search/list/detail/create/update）。
- MCP 关键 workflow 工具链可用（session_list/read/add/update/mark）。
- CI 门禁对失败场景可稳定拦截并输出可读诊断。

### Phase 3 - Default Cutover 与 Deprecation 执行

**输入**

- Phase 2 联调与 CI 运行数据。
- 兼容入口使用统计与风险评估。

**输出**

- `gmemory-service` 成为默认推荐入口。
- 旧命令进入 deprecation timeline（告警、只读文档、最终下线计划）。
- 完整运维 Runbook（启动、健康检查、故障排查、回滚）。

**风险**

- 少量外部脚本仍硬编码旧命令。
- 迁移窗口内文档与真实行为短暂不一致。

**回滚点**

- 保留一个 release 周期的 legacy 启动能力；必要时将默认入口切回双命令模式。

**验收标准**

- 默认文档、CI、发布脚本均以 `gmemory-service` 为主。
- 线上/本地问题可在统一日志与统一错误模型下定位。
- 兼容入口具备明确 EOL 日期与替代说明。

## 6. 统一规范

### 6.1 Error Model

- 统一错误结构（建议）：
  - `code`：稳定机器可读错误码（如 `INVALID_ARGUMENT`, `NOT_FOUND`）。
  - `message`：面向开发者的英文短句。
  - `details`：结构化上下文（字段级错误、依赖状态、hint）。
  - `request_id`：全链路排障主键。
- API 侧使用统一 JSON error envelope；MCP 侧映射到 MCP error，同时保留 `details`。
- 禁止返回仅字符串错误，必须可机读与可聚合。

### 6.2 Schema

- 使用单一 schema source（建议 Pydantic model + JSON Schema 导出）。
- 为关键响应增加 `schema_version`（或 header `X-Schema-Version`）。
- 变更策略：新增字段向后兼容；删除/改名字段必须走 deprecation 流程。

### 6.3 Logging

- 统一结构化日志字段：`timestamp`, `level`, `request_id`, `trace_id`, `module`, `op`, `latency_ms`, `status`。
- 业务关键维度补充：`session_id`, `memory_id`, `tool_name`, `agent`。
- 敏感信息脱敏：用户输入长文本与凭据字段默认不落盘明文。

### 6.4 Timeout / Retry / Idempotency

- timeout 基线：
  - 读操作默认较短超时（如 3~10s）。
  - 写操作默认更长超时（如 10~30s），并暴露可配置上限。
- retry 规则：仅对可重试错误与幂等操作启用指数退避；禁止对非幂等写入盲重试。
- idempotency：
  - 写接口支持 `Idempotency-Key`（header 或参数），服务端保留短期去重记录。
  - MCP 写工具增加 `idempotency_key` 参数并在 workflow 中推荐使用。

### 6.5 Deprecation

- 每个废弃项必须包含：`start_version`、`warning_window`、`removal_version`、替代方案。
- 在 warning window 内：
  - 运行时告警（日志 + CLI 提示）。
  - 文档双写（新命令 + 旧命令兼容说明）。
- 超过 removal 版本后移除实现并保留迁移指引。

## 7. Web 对接与联调门禁

### 7.1 本地联调步骤（门禁前置）

1. 启动 unified service（目标态）：

```bash
gmemory-service
```

2. 兼容入口回归（迁移期必须保留）：

```bash
gmemory-web
gmemory-mcp
```

3. 启动 Web 前端：

```bash
cd web
npm install
npm run dev
```

4. 联调检查项：

- Web 页面可完成搜索、列表、详情、创建/更新。
- MCP 核心 workflow 可执行。
- 错误场景（参数缺失、资源不存在、超时）返回统一 error model。

5. MCP 调试建议（至少一种）：

- 使用 Web `/mcp` 调试页（若项目已提供该页）。
- 或使用 MCP Inspector/CLI 直接连 `gmemory-service` 的 MCP adapter 做工具调用验证。

### 7.2 CI 门禁（必须阻断合并）

建议 CI 增加以下 stage（任一失败即 fail pipeline）：

- `backend-contract-check`：schema 快照与 error envelope 一致性校验。
- `service-smoke-test`：启动 `gmemory-service` 后执行 API + MCP 双路径 smoke。
- `web-integration-gate`：Web build + 基础联调脚本（至少覆盖 search 与写路径一次）。
- `compatibility-gate`：旧命令 `gmemory-web` / `gmemory-mcp` 仍可启动并通过最小化 smoke。

证据要求（建议写入 PR checklist）：

- 关键日志片段（含 `request_id`）。
- smoke 输出摘要（成功/失败条目）。
- 失败时附 troubleshooting 结论与修复链接。

### 7.3 故障排查（联调门禁相关）

优先按以下顺序：

1. 启动与配置检查：命令、端口、环境变量、配置键名是否一致。
2. 健康检查：API health endpoint 与 MCP tool list 是否可达。
3. 契约检查：错误码、字段名、schema_version 是否与基线一致。
4. 进程残留清理：排查端口占用与 orphan process 后重试。
5. 最小化复现：仅启动 `gmemory-service` + 单条 API/MCP 请求，确认问题归属。

## 8. 任务拆分建议（backend / web / qa）

### backend

- 设计并实现 `gmemory-service` 统一 bootstrap。
- 抽离 `Shared Service Layer`，去除协议层业务重复。
- 落地统一 error model、schema version、idempotency contract。
- 提供 compatibility wrapper 与 deprecation warning。

### web

- 适配统一 error envelope，确保前端错误提示与重试策略一致。
- 增加联调脚本（本地一键检查）与 `/mcp` 调试页（若采用页面调试）。
- 对接 CI `web-integration-gate`，沉淀失败截图/日志。

### qa

- 维护 API + MCP 双协议回归用例矩阵。
- 建立门禁阈值与失败分级（blocker/high/medium）。
- 执行 rollback 验证（feature flag 切换、旧命令回退可用性）。

## 9. 评审清单（执行前）

- 是否已冻结 Phase 0 契约并完成 cross-team 评审。
- 是否为每个 Phase 定义 owner、时间窗口、回滚责任人。
- CI 门禁是否真实可执行（不是文档化门禁）。
- 是否保留兼容入口并给出明确 deprecation timeline。
- 是否具备最小证据集：日志、smoke 输出、故障复盘模板。
