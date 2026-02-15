---
name: refine-memory
description: (opencode - Command) Deep clean, deduplicate, and consolidate memories using mcp-memory-service tools.
---

你现在的任务是担任 **GMemory 架构师**。你需要指挥 Subagent (`knowledge-archivist`) 对现有记忆库进行深度的**清洗、重构与升华**。

目标是把零散的“数据”变成系统的“智慧”，充分利用 `mcp-memory-service` 的向量检索与管理能力。

### 执行流程

1.  **基线建立**:
    *   调用 `check_database_health()` 获取当前记忆总量。
    *   （可选）调用 `get_cache_stats()` 查看服务性能状态。

2.  **委托执行 (Delegation)**:
    *   调用 `Task` 工具并指定 `subagent_type="knowledge-archivist"`。
    *   **Prompt 指令**:
        > "请对记忆库执行深度清洗。
        > 1. 使用 `list_memories(page_size=50)` 遍历记忆。
        > 2. 针对每一批次，或针对特定 Tag（如 `python`, `react`），执行以下操作：
        >    - **去重**: 发现内容高度相似的记忆，合并为一条核心记忆（使用 `store_memory`），并删除旧的（使用 `delete_memory`）。
        >    - **模式升华**: 如果发现多条关于同一问题的具体案例，提炼为一条通用的 **Pattern** 或 **Solution** 类型记忆。
        >    - **标签清洗**: 统一同义标签（如 `doc` -> `documentation`），重新存储并删除旧条目。
        > 3. 重点关注 `memory_type` 为 `note` 或未分类的条目，尝试将其升级为 `decision`, `solution` 或 `learning`。
        > 4. 报告每一步的变更（Added/Deleted Hash）。"

3.  **核心任务分解**:

    *   **Task A: 语义去重 (Semantic Deduplication)**
        *   使用 `retrieve_memory` 搜索常见关键词（如 "error", "setup", "config"）。
        *   检查返回结果的 `similarity_score`。若 > 0.85 且内容冗余，执行合并。

    *   **Task B: 标签标准化 (Tag Hygiene)**
        *   使用 `search_by_tag` 查找常见非标准标签。
        *   替换为标准标签体系（`preference`, `solution`, `architecture` 等）。

    *   **Task C: 垃圾回收 (Garbage Collection)**
        *   识别内容过短（< 10 chars）或无意义的记忆。
        *   直接 `delete_memory`。

4.  **结果验证**:
    *   Subagent 完成后，再次调用 `check_database_health()` 对比数量变化。
    *   随机抽取 3-5 条新生成的记忆 (`retrieve_memory`) 验证质量。

5.  **报告**:
    *   输出《记忆库进化报告》：
        *   **优化前/后数量**: N -> M
        *   **清理条目数**: D
        *   **新增/合并核心记忆**: C
        *   **高价值发现**: 列出 3 条本次提炼的最有价值的 Pattern/Insight。

### 注意事项

*   **删除需谨慎**: `delete_memory` 是不可逆的。在删除前确保新记忆已经成功 `store_memory`（拿到新的 `content_hash`）。
*   **API 限制**: 每次 `list_memories` 默认翻页，Subagent 需自行管理页码。
*   **原子性**: 尽量保持“读-改-写-删”的顺序，避免数据丢失。
