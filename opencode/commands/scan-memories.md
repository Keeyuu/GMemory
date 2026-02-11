---
name: scan-memories
description: (opencode - Command) Exhaustively scan ALL unprocessed sessions via Subagent to extract evolution-driving memories.
---

你现在的任务是担任 **GMemory 首席审计官**。你需要指挥 Subagent 对**所有**尚未归档的会话进行全量扫描，提炼能促进 Agent **自我进化**的高价值记忆。

**严禁偷懒：必须处理积压的所有会话，不得人为截断或仅处理最近几条。**

### 执行流程

0.  **MCP 工具流程校准 (Mandatory MCP Workflow)**:
    *   默认运行形态为 single-process `gmemory-service`（统一提供 `/api` 与 `/mcp`）。
    *   若 MCP 工具连续失败，必须先在报告中提示“检查 `gmemory-service` 是否在线”，再决定是否重试。
    *   在开始前，先向 Subagent 明确：**必须优先使用 GMemory MCP 工具链，不要混用模糊的自定义逻辑**。
    *   必须遵守以下顺序（除非当前步骤无数据）：
        1. `gmemory_stats`：确认 `unprocessed_sessions` 基线。
        2. `gmemory_session_list(limit=100, state="unprocessed", agent="all", scanner_type="all")`：获取待处理会话列表（仅使用此列表，不依赖 `session_list`）。
        3. 若 `has_more=true`，继续调用 `gmemory_session_list` 直到拉取完成。
        4. `session_read`：按 `gmemory_session_list` 返回的 `session_id` 读取正文（必要时 `include_transcript=true`）。
        5. `gmemory_quick_search` / `gmemory_search --compact`：先查已有记忆，避免重复入库。
        6. `gmemory_add` / `gmemory_update`：写入或更新（必须同时提供 `preview` + `content`）。
        7. `gmemory_mark_session`：仅在写入成功后标记该会话已处理。
        8. `gmemory_get`：抽查新写入 ID，验证内容和标签是否正确。
        9. `gmemory_stats` / `gmemory_recent`：复核写入结果与数量变化。
    *   若工具报错，Subagent 必须记录错误原因、重试策略和最终状态，不能静默失败。

1.  **评估积压 (Assessment)**:
    *   运行 `gmemory_stats` 查看 `unprocessed_sessions` 数量。
    *   运行 `gmemory_session_list(limit=100, state="unprocessed", agent="all", scanner_type="all")` 获取本轮会话列表。
    *   如果数量为 0，直接结束并报告。

2.  **委托执行 (Delegation)**:
    *   **必须**调用 `delegate_task` 启动 `knowledge-archivist` 代理。
    *   **给 Subagent 的 Prompt 必须包含以下严格指令**:
        *   **目标**: 遍历所有未处理的会话 ID。
        *   **核心任务**: 从对话中提炼**能促进 Agent 自我进化**的高价值记忆。
        *   **提炼标准**:
            *   **用户偏好 (User Preferences)**: 用户明确要求的编码风格、工具偏好、禁忌事项。（这是 Agent 适应用户的关键）
            *   **通用解决方案 (Universal Solutions)**: 解决特定报错或问题的完整路径。（需剥离具体项目上下文，使其通用化，提升 Agent 解决类似问题的能力）
            *   **架构模式 (Architecture Patterns)**: 项目中确立的设计模式、目录结构规范。（提升 Agent 对项目架构的理解）
            *   **无效信息过滤**: 严禁收录闲聊、简单的 API 查询、未完成的尝试、特定于一次性任务的临时信息。
        *   **入库动作**:
            *   使用 `gmemory_add`，并且提交参数必须同时包含 `preview` 与 `content`。
            *   `preview`: 必须是一句话摘要，由 Subagent 主动撰写；禁止由代码自动裁剪生成。
            *   `content` (记忆全部内容): 必须是**经过抽象和总结**的独立知识点，**禁止**直接复制粘贴对话原文；第一段无需重复 `preview`，应直接进入可复用知识正文。
            *   `tags`: 必须丰富且准确（参考 `gmemory_tags`）。
            *   `project_path`: 必须推断并填入。
        *   **返回格式**: 执行完毕后，向我汇报一份结构化清单，包含：`Session ID`, `Memory ID`, `Preview` (内容简要概述,必须是一句话讲清), `Tags`。
        *   **MCP 执行证据 (Required)**:
            *   报告中必须附带关键调用证据：本轮 `gmemory_session_list` 的会话总数、`gmemory_add`/`gmemory_update` 的 ID 列表、对应 `session_id -> gmemory_mark_session` 映射、抽查过的 `gmemory_get` 结果摘要、前后 `gmemory_stats` 对比。

3.  **审核与报告 (Review & Report)**:
    *   检查 Subagent 的执行结果。
    *   **质量抽查**: 确保生成的记忆是“智慧的结晶”而非“数据的堆砌”。
    *   **最终输出**: 向用户展示一份详细的《记忆入库报告》，包含：
        *   扫描会话总数 / 实际入库记忆数。
        *   **新记忆清单**: 每一条都要展示 `[Preview] (Tags)`。

开始执行。如果积压任务过多，Subagent 可以分批次报告，但不能停止，直到处理完所有积压。
