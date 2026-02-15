---
name: scan-memories
description: (opencode - Command) Review and audit recent memories in mcp-memory-service to ensure quality and consistency.
---

你现在的任务是担任 **GMemory 审计官**。由于当前环境无法直接扫描历史会话文件，你的主要职责是**审计已存入的近期记忆**，确保其质量、标签准确性，并清理重复或无效条目。

### 执行流程

1.  **服务健康检查**:
    *   调用 `check_database_health()` 确认服务在线且数据库连接正常。
    *   记录当前 `total_memories` 数量。

2.  **拉取近期记忆**:
    *   调用 `list_memories(page=1, page_size=20)` 获取最近存入的 20 条记忆。
    *   如果需要更深入审计，可翻页 (`page=2`, `page=3`...)。

3.  **质量评估 (Audit)**:
    *   **遍历**每一条记忆，检查以下指标：
        *   **内容质量**: 是否经过了提炼？（而不是直接复制的对话）是否包含足够上下文？
        *   **类型准确性**: `metadata.type` (或隐含类型) 是否符合 `preference`, `solution`, `decision` 等标准分类？
        *   **标签完整性**: 是否有足够的标签？标签是否准确？
    *   **识别问题**: 标记出内容空洞、重复、标签混乱的记忆。

4.  **修正与优化 (Refinement)**:
    *   **调用 Subagent** (`knowledge-archivist`) 或直接执行修正动作：
        *   **补充**: 对标签缺失的记忆，使用 `delete_memory` (旧) + `store_memory` (新) 的方式进行更新（目前 API 不支持直接 update，需通过替换实现）。
        *   **清理**: 对明显无效或重复的记忆，调用 `delete_memory(content_hash=...)`。
        *   **合并**: 发现多条相似记忆时，合并为一条高质量记忆存入，并删除旧条目。

5.  **报告输出**:
    *   向用户汇报审计结果：
        *   **健康状态**: 服务状态及总记忆数。
        *   **审计范围**: 检查了最近 N 条记忆。
        *   **优化行动**: 列出执行的删除、合并或重新录入操作。
        *   **质量评分**: 对当前近期记忆的整体质量给出简评（优/良/差）。

### 给 Subagent (Knowledge Archivist) 的指令模板 (如果使用委托)

```markdown
请审计以下记忆列表（或调用 list_memories 自行获取）：
1. 检查是否存在重复内容，若有，请合并。
2. 检查标签是否规范，若不规范，请重新存储并删除旧的。
3. 识别高价值但描述模糊的记忆，尝试根据你的知识库（Training Data）进行补全（慎用，确保准确）。
```

### 异常处理

*   若 `list_memories` 返回空，报告“当前无近期记忆”。
*   若工具调用失败，请记录错误并尝试重试一次。

**注意**: 本命令不再执行全量会话扫描（Legacy 模式），专注于**记忆库的维护与质量控制**。
