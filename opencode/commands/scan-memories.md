---
name: scan-memories
description: (opencode - Command) Exhaustively scan ALL unprocessed sessions via Subagent to extract evolution-driving memories.
---

你现在的任务是担任 **GMemory 首席审计官**。你需要指挥 Subagent 对**所有**尚未归档的会话进行全量扫描，提炼能促进 Agent **自我进化**的高价值记忆。

**严禁偷懒：必须处理积压的所有会话，不得人为截断或仅处理最近几条。**

### 执行流程

1.  **评估积压 (Assessment)**:
    *   运行 `gmemory_stats` 查看 `unprocessed_sessions` 的列表或数量。
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

3.  **审核与报告 (Review & Report)**:
    *   检查 Subagent 的执行结果。
    *   **质量抽查**: 确保生成的记忆是“智慧的结晶”而非“数据的堆砌”。
    *   **最终输出**: 向用户展示一份详细的《记忆入库报告》，包含：
        *   扫描会话总数 / 实际入库记忆数。
        *   **新记忆清单**: 每一条都要展示 `[Preview] (Tags)`。

开始执行。如果积压任务过多，Subagent 可以分批次报告，但不能停止，直到处理完所有积压。
