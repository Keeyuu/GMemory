---
name: refine-memory
description: (opencode - Command) Refine, deduplicate, and consolidate GMemory entries for higher quality and self-evolution.
---

你现在的任务是担任 **GMemory 首席架构师**。你需要指挥 Subagent 对现有记忆库进行深度的**清洗、重构与升华**。

目标是把零散的“数据”变成系统的“智慧”。

### 执行流程

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

3.  **审核与报告 (Review & Report)**:
    *   检查 Subagent 的操作记录。
    *   **最终输出**: 向用户展示一份《记忆库进化报告》，包含：
        *   记忆总数变化（优化前 vs 优化后）。
        *   **优化亮点**: 列出合并的关键知识点和新发现的模式。
        *   **下一步建议**: 基于当前记忆状态，建议用户补充哪些领域的知识。

开始执行。让记忆库焕然一新。
