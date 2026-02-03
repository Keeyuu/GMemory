# GMemory MVP 工作计划

## TL;DR

> **Quick Summary**: 实现本地 Agent 持久化记忆系统，通过 Python 脚本提供数据 I/O，Agent 负责提炼决策，使用 SQLite + sqlite-vec 存储。
> 
> **Deliverables**:
> - Python 核心库 (gmemory/)
> - 两个 OpenCode Skills (gmemory-refine, gmemory)
> - SQLite 数据库 (~/.gmemory/data.db)
> 
> **Estimated Effort**: Medium (3-5 天)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: 存储层 → Scanner → 命令实现 → Skills

---

## Context

### Original Request
设计一个本地 Agent 持久化记忆系统，结合 memex 的高效扫描和 opencode-mem 的智能提炼。

### 核心设计决策

| 维度 | 决策 |
|------|------|
| **语言** | Python |
| **数据源** | OpenCode 会话日志 (后期可扩展) |
| **存储** | SQLite + sqlite-vec，单文件 `~/.gmemory/data.db` |
| **Embedding** | 可配置 (默认 Ollama nomic-embed-text) |
| **提炼方式** | Agent 主导，脚本只做 I/O |
| **集成方式** | OpenCode Skills (轻量化) |
| **记忆隔离** | 全局存储 + 项目标签过滤 |

### 架构设计

```
用户下达意图 → Agent 加载 Skill → Agent 执行操作
                                      ↓
┌─────────────────────────────────────────────────────────────┐
│  提炼流程 (Agent 主导)                                        │
├─────────────────────────────────────────────────────────────┤
│  1. Agent 调用 fetch → 脚本返回未处理会话                      │
│  2. Agent 自己分析提炼内容                                    │
│  3. Agent 调用 save → 脚本存储 + 标记                         │
│  4. Agent 根据 has_more 决定是否继续                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  CRUD 流程 (Agent 调用)                                       │
├─────────────────────────────────────────────────────────────┤
│  search / add / update / delete / stats                     │
└─────────────────────────────────────────────────────────────┘
```

### 参考项目

| 项目 | 复用内容 |
|------|---------|
| C:\Code\memex | 增量扫描状态管理、RRF 混合搜索算法 |
| C:\Code\opencode-mem | SQLite + sqlite-vec 表结构、去重逻辑 |

---

## Work Objectives

### Core Objective
实现一个纯 Python 的本地 Agent 记忆系统，通过 OpenCode Skills 集成，支持会话提炼和记忆 CRUD。

### Concrete Deliverables
- `gmemory/` Python 包 (可通过 `python -m gmemory` 调用)
- `skills/gmemory-refine/SKILL.md`
- `skills/gmemory/SKILL.md`
- `~/.gmemory/data.db` 数据库

### Definition of Done
- [x] `python -m gmemory fetch --limit 5` 返回 OpenCode 未处理会话
- [x] `python -m gmemory save --session-id xxx --content "..." --tags "a,b"` 成功存储
- [x] `python -m gmemory search "query"` 返回语义相似结果 (需要 Ollama，无 Ollama 时优雅降级)
- [x] Skills 可通过 `npx @anthropic/skill add ./skills/gmemory` 添加

### Must Have
- SQLite + sqlite-vec 存储
- OpenCode 数据读取
- fetch / save / mark 命令
- search / add / update / delete 命令
- 向量嵌入 (Ollama)
- JSON 输出格式

### Must NOT Have (Guardrails)
- ❌ 不做 Hook/事件拦截
- ❌ 不启动独立服务/进程
- ❌ 不做 MCP Server
- ❌ 不做自动提炼 (Agent 主导)
- ❌ 不做 Web UI
- ❌ 暂不支持 Claude/Codex 等其他 Agent

---

## Database Schema

```sql
-- ~/.gmemory/data.db

-- 1. 记忆表
CREATE TABLE memories (
    id TEXT PRIMARY KEY,              -- UUID
    content TEXT NOT NULL,            -- 提炼后的技术要点
    tags TEXT,                        -- JSON array: ["auth", "jwt"]
    importance TEXT DEFAULT 'medium', -- high/medium/low
    memory_type TEXT,                 -- decision/solution/pattern/preference
    
    -- 来源追踪
    agent TEXT NOT NULL DEFAULT 'opencode',
    source_session_id TEXT,
    project_path TEXT,
    project_name TEXT,
    
    -- 时间
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- 2. 向量索引表
CREATE VIRTUAL TABLE memory_vectors USING vec0(
    memory_id TEXT PRIMARY KEY,
    embedding float[768]
);

-- 3. 处理状态表
CREATE TABLE processed_sessions (
    agent TEXT NOT NULL,
    session_id TEXT NOT NULL,
    processed_at INTEGER NOT NULL,
    PRIMARY KEY (agent, session_id)
);

-- 索引
CREATE INDEX idx_memories_agent ON memories(agent);
CREATE INDEX idx_memories_project ON memories(project_path);
CREATE INDEX idx_memories_created ON memories(created_at DESC);
```

---

## Project Structure

```
gmemory/
├── skills/
│   ├── gmemory-refine/
│   │   └── SKILL.md
│   └── gmemory/
│       └── SKILL.md
│
├── gmemory/
│   ├── __init__.py
│   ├── __main__.py           # CLI 入口
│   ├── config.py             # 配置管理
│   ├── models.py             # 数据模型
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py       # SQLite + sqlite-vec
│   │   └── embedder.py       # 向量嵌入
│   │
│   ├── scanner/
│   │   ├── __init__.py
│   │   └── opencode.py       # 读取 OpenCode 数据
│   │
│   └── commands/
│       ├── __init__.py
│       ├── fetch.py
│       ├── save.py
│       ├── mark.py
│       ├── search.py
│       ├── add.py
│       ├── update.py
│       ├── delete.py
│       └── stats.py
│
├── config.toml
├── pyproject.toml
└── README.md
```

---

## Command Specifications

### Refine Commands

#### fetch
```bash
python -m gmemory fetch [--limit N] [--agent opencode]
```
**Output:**
```json
{
  "sessions": [
    {
      "session_id": "ses_abc123",
      "agent": "opencode",
      "project_path": "/path/to/project",
      "project_name": "my-project",
      "started_at": "2024-02-03T10:00:00Z",
      "messages": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
      ]
    }
  ],
  "has_more": true,
  "remaining": 12
}
```

#### save
```bash
python -m gmemory save \
  --session-id "ses_abc123" \
  --content "技术要点" \
  --tags "auth,jwt" \
  --importance "high" \
  --type "solution"
```
**Output:**
```json
{"memory_id": "mem_xyz", "created": true, "session_marked": true}
```

#### mark
```bash
python -m gmemory mark --session-id "ses_abc123"
```
**Output:**
```json
{"session_id": "ses_abc123", "marked": true}
```

### CRUD Commands

#### search
```bash
python -m gmemory search "query" [--project PATH] [--tags t1,t2] [--limit N]
```
**Output:**
```json
{
  "results": [
    {"id": "mem_x", "content": "...", "tags": [...], "similarity": 0.89}
  ],
  "total": 1
}
```

#### add
```bash
python -m gmemory add --content "内容" --tags "t1,t2" --importance "medium"
```
**Output:** `{"id": "mem_x", "created": true}`

#### update
```bash
python -m gmemory update "mem_id" [--content "新内容"] [--tags "t1,t2"]
```
**Output:** `{"id": "mem_x", "updated": true}`

#### delete
```bash
python -m gmemory delete "mem_id"
```
**Output:** `{"id": "mem_x", "deleted": true}`

#### stats
```bash
python -m gmemory stats
```
**Output:**
```json
{
  "total_memories": 156,
  "unprocessed_sessions": 12,
  "by_project": {...},
  "by_importance": {...}
}
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (基础设施):
├── Task 1: 项目初始化 + pyproject.toml
├── Task 2: 数据模型 (models.py)
└── Task 3: 配置管理 (config.py)

Wave 2 (核心模块):
├── Task 4: 存储层 (database.py + embedder.py)
├── Task 5: Scanner (opencode.py)
└── Task 6: 命令框架 (__main__.py)

Wave 3 (命令实现):
├── Task 7: fetch + save + mark
├── Task 8: search
└── Task 9: add + update + delete + stats

Wave 4 (集成):
├── Task 10: Skill 文件
└── Task 11: 集成测试
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|------------|--------|
| 1, 2, 3 | None | 4, 5, 6 |
| 4 | 2, 3 | 7, 8, 9 |
| 5 | 2, 3 | 7 |
| 6 | 3 | 7, 8, 9 |
| 7 | 4, 5, 6 | 10, 11 |
| 8 | 4, 6 | 10, 11 |
| 9 | 4, 6 | 10, 11 |
| 10 | 7, 8, 9 | 11 |
| 11 | 10 | None |

---

## TODOs

### Wave 1: 基础设施

- [x] 1. 项目初始化

  **What to do**:
  - 创建 pyproject.toml (使用 hatchling 或 setuptools)
  - 定义依赖: sqlite-vec, ollama, click, tomli
  - 创建基础目录结构

  **Must NOT do**:
  - 不使用 poetry (保持简单)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: 4, 5, 6

  **References**:
  - `C:\Code\opencode-mem\package.json` - 依赖参考

  **Acceptance Criteria**:
  - [ ] `pip install -e .` 成功
  - [ ] `python -m gmemory --help` 显示帮助

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: pip install works
    Tool: Bash
    Steps:
      1. cd C:\Code\GMemory && pip install -e .
      2. python -m gmemory --help
    Expected: Shows help message with available commands
  ```

  **Commit**: YES
  - Message: `feat(init): project setup with pyproject.toml`

---

- [x] 2. 数据模型

  **What to do**:
  - 创建 gmemory/models.py
  - 定义 Memory, Session, Message 等 dataclass
  - 使用 Python 3.10+ 语法

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1

  **References**:
  - `C:\Code\opencode-mem\src\types\memory.ts` - Memory 结构参考

  **Acceptance Criteria**:
  - [ ] Memory dataclass 包含: id, content, tags, importance, agent, source_session_id, project_path
  - [ ] 支持 to_dict() 和 from_dict() 方法

  **Commit**: YES
  - Message: `feat(models): add Memory and Session dataclasses`

---

- [x] 3. 配置管理

  **What to do**:
  - 创建 gmemory/config.py
  - 创建 config.toml 模板
  - 支持从 ~/.gmemory/config.toml 加载配置
  - 默认配置: db_path, embedding provider/model/dimension

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1

  **References**:
  - `C:\Code\memex\memex.toml` - 配置格式参考

  **Acceptance Criteria**:
  - [ ] Config dataclass 包含所有配置项
  - [ ] 支持默认值
  - [ ] config.toml 模板文件存在

  **Commit**: YES
  - Message: `feat(config): add configuration management`

---

### Wave 2: 核心模块

- [x] 4. 存储层实现

  **What to do**:
  - 创建 gmemory/storage/database.py
  - 实现 MemoryDatabase 类
  - 初始化 SQLite + sqlite-vec
  - 实现 CRUD 方法
  - 创建 gmemory/storage/embedder.py
  - 实现 Ollama embedding 调用

  **Must NOT do**:
  - 不实现分片 (MVP 不需要)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocked By**: 2, 3

  **References**:
  - `C:\Code\opencode-mem\src\services\sqlite\vector-search.ts` - sqlite-vec 用法
  - 之前分析的 sqlite-vec Python 示例

  **Acceptance Criteria**:
  - [ ] sqlite-vec 扩展加载成功
  - [ ] memories 和 memory_vectors 表创建成功
  - [ ] add_memory / search_memories / update_memory / delete_memory 方法可用
  - [ ] embedder.embed(text) 返回向量

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Database initialization
    Tool: Bash
    Steps:
      1. python -c "from gmemory.storage.database import MemoryDatabase; db = MemoryDatabase(); print('OK')"
    Expected: Prints "OK", creates ~/.gmemory/data.db
  ```

  **Commit**: YES
  - Message: `feat(storage): implement SQLite + sqlite-vec storage layer`

---

- [x] 5. OpenCode Scanner

  **What to do**:
  - 创建 gmemory/scanner/opencode.py
  - 实现读取 OpenCode 数据库
  - 获取会话列表和消息内容
  - 过滤已处理的会话

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocked By**: 2, 3

  **References**:
  - `C:\Code\memex\src\ingest.rs` - collect_opencode_files 函数
  - `~/.local/share/opencode/storage/` - OpenCode 数据目录结构

  **Acceptance Criteria**:
  - [ ] 能读取 OpenCode 会话列表
  - [ ] 能获取会话的消息内容
  - [ ] 能过滤已处理的会话 (查询 processed_sessions 表)

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Scan OpenCode sessions
    Tool: Bash
    Steps:
      1. python -c "from gmemory.scanner.opencode import OpenCodeScanner; s = OpenCodeScanner(); print(len(s.get_unprocessed_sessions(limit=5)))"
    Expected: Prints a number >= 0
  ```

  **Commit**: YES
  - Message: `feat(scanner): implement OpenCode session reader`

---

- [x] 6. 命令行框架

  **What to do**:
  - 创建 gmemory/__main__.py
  - 使用 click 实现 CLI
  - 定义所有命令的骨架 (fetch, save, mark, search, add, update, delete, stats)
  - 统一 JSON 输出格式

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocked By**: 3

  **References**:
  - `C:\Code\memex\src\cli.rs` - CLI 结构参考

  **Acceptance Criteria**:
  - [ ] `python -m gmemory --help` 显示所有命令
  - [ ] 每个命令有 --help 支持
  - [ ] 输出格式为 JSON

  **Commit**: YES
  - Message: `feat(cli): add command line framework with click`

---

### Wave 3: 命令实现

- [x] 7. fetch + save + mark 命令

  **What to do**:
  - 实现 gmemory/commands/fetch.py
  - 实现 gmemory/commands/save.py
  - 实现 gmemory/commands/mark.py
  - 集成到 CLI

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 9)
  - **Blocked By**: 4, 5, 6

  **References**:
  - 上文定义的命令规格

  **Acceptance Criteria**:
  - [ ] `python -m gmemory fetch --limit 2` 返回会话 JSON
  - [ ] `python -m gmemory save --session-id xxx --content "test" --tags "a,b"` 成功
  - [ ] `python -m gmemory mark --session-id xxx` 成功
  - [ ] save 后再次 fetch 不返回该会话

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Full refine workflow
    Tool: Bash
    Steps:
      1. python -m gmemory fetch --limit 1
      2. 获取返回的 session_id
      3. python -m gmemory save --session-id <id> --content "test" --tags "test"
      4. python -m gmemory fetch --limit 1 检查不包含该 session
    Expected: Workflow completes without error
  ```

  **Commit**: YES
  - Message: `feat(commands): implement fetch, save, mark commands`

---

- [x] 8. search 命令

  **What to do**:
  - 实现 gmemory/commands/search.py
  - 调用 embedder 生成查询向量
  - 调用 database 执行向量搜索
  - 支持 --project, --tags, --limit 过滤

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocked By**: 4, 6

  **References**:
  - `C:\Code\memex\src\cli.rs` - 混合搜索逻辑

  **Acceptance Criteria**:
  - [ ] `python -m gmemory search "test"` 返回相似记忆
  - [ ] 返回结果包含 similarity 分数
  - [ ] --limit 参数生效

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Search returns results
    Tool: Bash
    Preconditions: At least one memory exists
    Steps:
      1. python -m gmemory add --content "JWT authentication" --tags "auth"
      2. python -m gmemory search "authentication"
    Expected: Returns result with similarity > 0.5
  ```

  **Commit**: YES
  - Message: `feat(commands): implement search command with vector similarity`

---

- [x] 9. add + update + delete + stats 命令

  **What to do**:
  - 实现 gmemory/commands/add.py
  - 实现 gmemory/commands/update.py
  - 实现 gmemory/commands/delete.py
  - 实现 gmemory/commands/stats.py

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocked By**: 4, 6

  **Acceptance Criteria**:
  - [ ] `python -m gmemory add --content "test"` 返回新 ID
  - [ ] `python -m gmemory update <id> --content "new"` 成功
  - [ ] `python -m gmemory delete <id>` 成功
  - [ ] `python -m gmemory stats` 返回统计信息

  **Commit**: YES
  - Message: `feat(commands): implement add, update, delete, stats commands`

---

### Wave 4: 集成

- [x] 10. Skill 文件

  **What to do**:
  - 创建 skills/gmemory-refine/SKILL.md
  - 创建 skills/gmemory/SKILL.md
  - 按照上文设计编写文档

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 11)
  - **Blocked By**: 7, 8, 9

  **Acceptance Criteria**:
  - [ ] 两个 SKILL.md 文件存在
  - [ ] 包含正确的命令格式和示例

  **Commit**: YES
  - Message: `docs(skills): add gmemory and gmemory-refine skill files`

---

- [x] 11. 集成测试

  **What to do**:
  - 端到端测试完整流程
  - 验证所有命令正常工作
  - 验证 Skills 可添加到 OpenCode

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: [`python-testing`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: 10

  **Acceptance Criteria**:
  - [ ] fetch → save → search 完整流程通过
  - [ ] add → update → delete 流程通过
  - [ ] `npx @anthropic/skill add ./skills/gmemory` 成功 (如适用)

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: End-to-end workflow
    Tool: Bash
    Steps:
      1. python -m gmemory stats (初始状态)
      2. python -m gmemory add --content "Test memory" --tags "test"
      3. python -m gmemory search "test"
      4. python -m gmemory stats (验证 total +1)
    Expected: All commands succeed, stats show 1 memory
  ```

  **Commit**: YES
  - Message: `test: add integration tests for gmemory`

---

## Commit Strategy

| After Task | Message | Verification |
|------------|---------|--------------|
| 1 | `feat(init): project setup` | pip install -e . |
| 2 | `feat(models): add dataclasses` | import gmemory.models |
| 3 | `feat(config): configuration` | config loads |
| 4 | `feat(storage): sqlite-vec layer` | db initializes |
| 5 | `feat(scanner): opencode reader` | sessions read |
| 6 | `feat(cli): command framework` | --help works |
| 7 | `feat(commands): fetch/save/mark` | refine flow works |
| 8 | `feat(commands): search` | search works |
| 9 | `feat(commands): crud + stats` | all commands work |
| 10 | `docs(skills): skill files` | files exist |
| 11 | `test: integration tests` | e2e passes |

---

## Success Criteria

### Verification Commands
```bash
# 基础检查
python -m gmemory --help

# fetch 测试
python -m gmemory fetch --limit 2

# CRUD 测试
python -m gmemory add --content "Test" --tags "test"
python -m gmemory search "Test"
python -m gmemory stats
```

### Final Checklist
- [ ] 所有命令返回 JSON 格式
- [ ] sqlite-vec 向量搜索正常工作
- [ ] OpenCode 会话读取正常
- [ ] processed_sessions 标记机制正常
- [ ] Skills 文档完整
