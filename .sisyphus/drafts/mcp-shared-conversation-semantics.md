# Draft: MCP Shared Conversation Semantics

## Requirements (confirmed)
- 语义需要调整: 任何 agent 理论上都可以通过 MCP 获取全部对话并进行提炼。
- 本地部署要求: 对话访问能力应为可共享能力, 不应被单一 agent 或单一视图误导。

## Technical Decisions
- 当前阶段先做语义和定义对齐, 再落到接口行为与统计口径。
- 将区分三类口径: 原始会话库存、可枚举视图、待处理队列。

## Research Findings
- `unprocessed_sessions` 来自 GMemory 统计逻辑, 不是 `session_list` 直接结果。
- `session_list` 仅代表某个会话视图, 不能当作全局库存口径。

## Scope Boundaries
- INCLUDE: 统一术语、统一统计口径、定义跨 agent 共享访问模型。
- EXCLUDE: 暂不直接执行实现代码与数据修复动作。

## Open Questions
- 共享语义优先落在哪一层: 文档定义、MCP API 返回结构、还是统计命令口径?
- 是否要求默认返回全局聚合视图, 同时保留按 agent/项目过滤?
