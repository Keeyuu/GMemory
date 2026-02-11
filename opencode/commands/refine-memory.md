---
name: refine-memory
description: (opencode - Command) Refine, deduplicate, and consolidate GMemory entries for higher quality and self-evolution.
---

你现在的任务是担任 **GMemory 首席架构师**。你需要指挥 Subagent 对现有记忆库进行深度的**清洗、重构与升华**。

目标是把零散的“数据”变成系统的“智慧”。

### 执行流程

0.  **MCP 工具流程校准 (Mandatory MCP Workflow)**:
    *   在开始前，先向 Subagent 明确：**所有清洗/合并动作必须通过 GMemory MCP 工具执行并可追溯**。
    *   推荐固定流程：
        1. `gmemory_stats` + `gmemory_tags`：建立质量与标签基线。
        2. `gmemory_search --compact` / `gmemory_quick_search`：发现候选重复和低质量条目。
        3. `gmemory_get`：读取候选记忆完整内容后再决定 merge/update/delete。
        4. `gmemory_add` / `gmemory_update` / `gmemory_delete`：执行重构动作（`add/update` 必须带 `preview` + `content`）。
        5. `gmemory_get`：抽查新核心记忆，验证字段质量。
        6. `gmemory_stats` / `gmemory_tag`：复核结果是否符合预期。
    *   禁止“只看 preview 就直接删改”；必须先 `gmemory_get` 再决策。

1.  **全局诊断 (Diagnosis)**:
    *   运行 `gmemory_stats` 获取当前健康度。
    *   运行 `gmemory_tags` 分析标签分布，识别混乱或冗余的标签（如同义词）。

2.  **委托执行 (Delegation)**:
    *   **必须**调用 `delegate_task` 启动 `knowledge-archivist` 代理。
    *   **给 Subagent 的 Prompt 必须包含以下严格指令**:
        *   **任务 A: 标签清洗 (Tag Hygiene)**
            *   识别并合并同义标签（例如：`skill` vs `skills`, `doc` vs `documentation`）。
            *   为标签稀少（<2个）的记忆补充标签。
            *   使用 `gmemory_update` 执行修改（必须同时提供 `preview` 与 `content`）。
        *   **任务 B: 去重与合并 (Deduplication & Consolidation)**
            *   主动搜索内容高度相似的记忆（使用 `gmemory_search` 配合 `limit`）。
            *   **动作**: 将多条碎片化记忆**合并**为一条内容更全面、结构更清晰的“核心记忆” (Core Memory)。
            *   合并后，创建新记忆，并删除旧的碎片记忆。
            *   **Preview 必填**: `gmemory_add`/`gmemory_update` 必须显式传入 `preview`，不可由代码自动裁剪或从 `content` 派生。
        *   **任务 C: 模式升华 (Pattern Recognition)**
            *   识别反复出现的问题模式（例如：特定环境下的重复报错）。
            *   **动作**: 提炼出一条 **SOP (标准作业程序)** 或 **最佳实践 (Best Practice)** 类记忆。
            *   标记此类高价值记忆为 `importance: high`。
        *   **任务 D: 清理 (Cleanup)**
            *   识别并删除内容空洞、上下文缺失且无法修复的“垃圾记忆”。
        *   **写入字段规范 (Required Fields)**
            *   `preview`: 必须是一句话摘要，由 Subagent 主动撰写。
            *   `content`: 必须是提炼后的完整记忆正文；第一段不需要重复 `preview`，直接展开背景、结论或 SOP。
            *   严禁将 `preview` 作为 `content` 首段的自动裁剪结果。
        *   **返回格式**: 执行完毕后，向我汇报一份结构化清单：
            *   `Merged`: [旧ID列表] -> [新ID] (主题)
            *   `Cleaned`: [ID] (原因)
            *   `Refined`: [ID] (操作: 标签优化/内容补充)
            *   `Insights`: [ID] (新发现的高层模式预览)
            *   `MCP Evidence`: `stats_before` / `stats_after`、抽查 `gmemory_get` 的 ID 与结论。

3.  **审核与报告 (Review & Report)**:
    *   检查 Subagent 的操作记录。
    *   **最终输出**: 向用户展示一份《记忆库进化报告》，包含：
        *   记忆总数变化（优化前 vs 优化后）。
        *   **优化亮点**: 列出合并的关键知识点和新发现的模式。
     *   **下一步建议**: 基于当前记忆状态，建议用户补充哪些领域的知识。

### 变更后回归建议（主 Agent 执行）

若本轮清洗/合并任务伴随 MCP 工具或分页契约调整，报告末尾应附带回归提醒：

1. 执行 `tests/test_fetch.py`、`tests/test_mcp.py`、`tests/test_service.py`。
2. 执行 `pm2 restart gmemory-service`。
3. 使用 `opencode run` 验证 `gmemory_stats` 与 `gmemory_session_list` 的运行态结果。

开始执行。让记忆库焕然一新。
