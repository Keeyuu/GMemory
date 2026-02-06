# GMemory

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-156%20passed-brightgreen.svg)]()

**OpenCode 本地 Agent 持久化记忆系统**

[English Documentation](README.md)

## 概述

GMemory 是一个轻量级 CLI 工具，为 AI 编程助手提供持久化记忆能力。它扫描 OpenCode 会话日志，支持关键信息的提炼，并将记忆存储在本地 SQLite 数据库中，支持混合向量 + 全文搜索。

**设计理念**：最小依赖、本地优先、CLI 驱动。无云端依赖。

## 功能特性

### 核心能力
- **混合搜索**：结合向量相似度 (sqlite-vec) + FTS5 全文搜索，支持加权评分
- **渐进式披露**：`search --compact` → `get <ids>` 工作流，最小化 Token 消耗
- **本地嵌入**：FastEmbed + nomic-embed-text-v1.5 (768 维) - 无需外部 API 调用
- **增量扫描**：通过 content_hash/mtime/size 跟踪文件变化，跳过未修改的会话

### 数据管理
- **隐私保护**：`<private>` 标签过滤，存储前剥离敏感内容
- **记忆生命周期**：Supersede 机制，更新记忆同时保留历史
- **去重**：查找并合并相似/重复记忆（vector、simhash、minhash）
- **数据生命周期**：清理、压缩、重建索引命令，支持长期维护

### 搜索与发现
- **时效性加权**：可选的时间衰减评分，优先显示近期记忆
- **搜索可解释性**：详细的评分分解，展示 vector/FTS/recency 贡献
- **双向量索引**：可选的基于标签的语义搜索，提升匹配效果
- **搜索配置文件**：预配置的搜索预设，适用于常见场景

### 运维
- **Schema 迁移**：版本化数据库 Schema，启动时自动迁移
- **数据验证**：写入路径的字段级验证，确保数据质量
- **诊断**：内置 sqlite-vec、维度、Schema 状态健康检查
- **导出**：导出记忆和报告为 Markdown 或 JSON

### 可扩展性
- **嵌入配置文件**：多嵌入模型配置，支持迁移工作流
- **数据源适配器**：可插拔架构，解析不同 Agent 日志格式
- **快捷命令**：常用高频操作的快捷命令

## 安装

### 快速安装（推荐）

**Windows (PowerShell):**
```powershell
git clone https://github.com/Keeyuu/GMemory.git
cd GMemory
powershell -ExecutionPolicy Bypass -File install.ps1

# 跳过 Python 模块安装
powershell -ExecutionPolicy Bypass -File install.ps1 -SkipModules
```

**Linux/macOS:**
```bash
git clone https://github.com/Keeyuu/GMemory.git
cd GMemory
chmod +x install.sh && ./install.sh

# 跳过 Python 模块安装
./install.sh --skip-modules
```

安装脚本会：
1. 安装 GMemory 包（可跳过）
2. 创建数据目录 `~/.gmemory/`

### 手动安装

```bash
# 从源码安装
pip install -e .

# 或使用 uv（推荐）
uv pip install -e .
```

### 安装选项

| 选项 | 描述 |
|------|------|
| `--dev` | 安装开发依赖（pytest, mypy） |
| `--force` | 强制重新安装（先卸载再安装） |
| `--skip-modules` | 跳过 Python 模块安装 |

**升级**：重新运行安装脚本即可升级到最新版本。

**依赖要求**：Python 3.10+、sqlite-vec、fastembed

## 快速开始

```bash
# 1. 获取未处理的会话
gmemory process --limit=5

# 2. 保存提炼的记忆
gmemory save --session-id=<id> --content="关于 X 的关键洞察" --tags="python,api"

# 3. 搜索记忆
gmemory search "认证模式" --compact

# 4. 获取完整内容
gmemory get <memory-id>
```

## MCP 服务

```bash
# 启动 MCP Server（stdio）
gmemory-mcp

# 等价方式
python -m gmemory.mcp
```

客户端配置可参考 `docs/mcp-config.example.json`。

## Web API 与前端

```bash
# 启动 Web API（默认：127.0.0.1:8765）
gmemory-web

# 启动前端开发服务器
cd web
npm install
npm run dev
```

生产预览：

```bash
cd web
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
```

使用 PM2 后台保活 Web API：

```bash
# Windows（推荐，无额外终端窗口）
pm2 start "C:/Code/GMemory/.venv/Scripts/pythonw.exe" --name gmemory-web --cwd "C:/Code/GMemory" -- -m gmemory.webapi

# 跨平台/基础方式
pm2 start uv --name gmemory-web --cwd "C:/Code/GMemory" -- run gmemory-web

pm2 save
pm2 status gmemory-web
```

Windows 说明：PM2 启动 `uv.exe` 时可能会弹出一个终端窗口。使用上面的 `pythonw.exe` 启动方式可避免额外终端窗口。

### Preview-First 工作流（Web）

- 列表/搜索/Dashboard 卡片默认优先展示 `preview`。
- 记忆详情页将 `Preview` 与 `Full Content` 分区展示。
- 若 preview 缺失，不视为错误：前端会从内容自动派生预览，支持继续手工编辑/删除。

### 记忆利用率统计

- 每条记忆新增 `access_count` 与 `last_accessed_at`（Schema migration v6）。
- 非 Web 按 ID 读取（`gmemory get`、MCP `gmemory_get`）默认会增加访问计数。
- Web 详情读取（`GET /api/memories/{id}`）不计入访问次数，避免页面浏览污染统计。
- `GET /api/stats` 增加 `top_hot` 与 `top_cold`，用于淘汰/改进决策。

### 手工验收清单

1. 打开 Dashboard，确认 `Top Hot` / `Top Cold` 区块可见。
2. 点击热榜项进入详情页，确认同时显示 `Preview` 与 `Full Content`。
3. 调用 Web 详情接口，确认访问计数不增加。
4. 执行 `gmemory get <id>`，确认访问计数增加。

### 使用 Edge 的 Playwright MCP 配置

如果你使用 Edge 进行浏览器 MCP 自动化，可在 OpenCode 配置中加入：

```json
"playwright": {
  "command": ["npx", "-y", "@playwright/mcp@latest", "--browser", "msedge"],
  "enabled": true,
  "type": "local"
}
```

## 命令参考

### 核心命令

| 命令 | 描述 |
|------|------|
| `fetch` | 从 OpenCode 日志获取未处理的会话 |
| `process` | 工作流入口：获取会话供审阅 |
| `save` | 保存提炼的记忆并标记会话已处理 |
| `search` | 混合/向量/FTS 搜索，支持过滤 |
| `get` | 通过 ID 获取完整记忆内容 |
| `list` | 分页浏览记忆 |
| `add` | 手动添加记忆 |
| `update` | 更新现有记忆 |
| `delete` | 删除记忆 |
| `stats` | 显示系统统计 |

### 工作流命令

| 命令 | 描述 |
|------|------|
| `mark` | 标记会话已处理（不保存记忆） |
| `mark-all` | 批量标记多个会话已处理 |
| `backlog` | 显示会话积压状态和工作流建议 |
| `session-report` | 生成会话级聚合报告 |
| `session-detail` | 获取特定会话的详细信息 |

### 搜索与发现

| 命令 | 描述 |
|------|------|
| `profiles` | 列出可用的搜索配置文件 |
| `q` | 快速搜索快捷方式（紧凑模式） |
| `recent` | 显示最近的记忆 |
| `today` | 显示今日活动摘要 |
| `tag` | 按标签查找记忆 |
| `tags` | 列出所有标签及计数 |

### 去重与导出

| 命令 | 描述 |
|------|------|
| `dedupe` | 查找相似/重复记忆组 |
| `merge` | 合并多个记忆为一个 |
| `auto-dedupe` | 自动查找并合并近似重复项 |
| `session-export` | 导出会话记忆为 Markdown/JSON |
| `report-export` | 导出会话报告为 Markdown/JSON |
| `export` | 按 ID 或过滤条件导出记忆 |

### 维护

| 命令 | 描述 |
|------|------|
| `rebuild` | 重建嵌入和/或 FTS 索引 |
| `diagnostics` | 显示数据库健康状态和配置 |
| `health` | 检查索引健康状态并识别问题 |
| `purge` | 根据保留策略删除旧记忆 |
| `compact` | 压缩和优化数据库 |
| `reindex` | 重建数据库索引（嵌入、FTS、标签） |
| `lifecycle-stats` | 显示记忆年龄分布和生命周期信息 |

### 配置

| 命令 | 描述 |
|------|------|
| `config-templates` | 列出可用的配置模板 |
| `config-generate` | 从模板生成配置文件 |
| `config-init` | 初始化项目级配置 |
| `config-show` | 显示当前生效的配置 |
| `embedding-profiles` | 列出/显示嵌入模型配置文件 |
| `embedding-check` | 切换前检查兼容性 |
| `embedding-switch` | 切换到不同的嵌入配置文件 |

### 错误管理

| 命令 | 描述 |
|------|------|
| `scan-runs` | 列出最近的扫描运行 |
| `scan-errors` | 列出扫描错误供手动恢复 |
| `scan-errors-resolve` | 标记扫描错误为已解决 |
| `scan-errors-summary` | 显示扫描错误摘要和建议 |
| `scan-errors-batch-resolve` | 按类型批量解决扫描错误 |

## 搜索

### 搜索选项

```bash
gmemory search "查询" \
  --profile=recent \        # 使用预设配置文件
  --mode=hybrid \           # hybrid（默认）、vector、fts
  --compact \               # 仅返回预览（节省 Token）
  --recency=0.3 \           # 近期记忆权重 (0.0-1.0)
  --project=/path \         # 按项目过滤
  --tags=python,api \       # 按标签过滤
  --include-superseded \    # 包含已替换的记忆
  --explain \               # 显示详细评分分解
  --use-tag-index \         # 启用双向量搜索
  --tag-weight=0.3 \        # 标签相似度权重 (0.0-1.0)
  --min-score=0.2           # 最低分数阈值 (0.0-1.0)
```

### 搜索配置文件

| 配置文件 | 模式 | 时效性 | 标签 | 描述 |
|----------|------|--------|------|------|
| `balanced` | hybrid | 0.0 | - | 默认平衡搜索（向量 + FTS） |
| `semantic` | vector | 0.0 | - | 纯语义相似度 |
| `keyword` | fts | 0.0 | - | 全文关键词搜索 |
| `recent` | hybrid | 0.4 | - | 中等时效性提升 |
| `very-recent` | hybrid | 0.7 | - | 强时效性提升 |
| `tag-heavy` | hybrid | 0.0 | 0.6 | 优先标签相似度 |
| `tag-only` | hybrid | 0.0 | 0.8 | 主要按标签搜索 |
| `fresh-tags` | hybrid | 0.3 | 0.5 | 标签 + 时效性组合 |

```bash
# 列出可用配置文件
gmemory profiles

# 使用配置文件
gmemory search "认证" --profile=recent
```

### 快捷命令

```bash
# 快速搜索（紧凑模式）
gmemory q "认证"
gmemory q "API 设计" -n 10

# 最近的记忆
gmemory recent              # 最近 7 天
gmemory recent -d 30        # 最近 30 天

# 今日摘要
gmemory today

# 按标签浏览
gmemory tag python
gmemory tags                # 列出所有标签
```

## 去重

查找并合并相似/重复记忆：

```bash
# 查找重复组
gmemory dedupe                          # 默认阈值 0.85
gmemory dedupe --threshold=0.90         # 更严格的匹配
gmemory dedupe --strategy=simhash       # 使用 SimHash（更快）
gmemory dedupe --strategy=minhash       # 使用 MinHash

# 合并记忆
gmemory merge mem1 mem2 mem3 --dry-run  # 预览
gmemory merge mem1 mem2 --keep=mem2     # 保留 mem2 为主

# 自动去重
gmemory auto-dedupe                     # 预览
gmemory auto-dedupe --apply             # 执行
```

**策略说明：**

| 策略 | 描述 | 适用场景 |
|------|------|----------|
| `vector` | 使用嵌入的语义相似度 | 最准确 |
| `simhash` | 局部敏感哈希 | 快速，近似重复 |
| `minhash` | Jaccard 相似度估计 | 内容重叠检测 |

## 配置

### 配置文件

默认位置：`~/.gmemory/config.json`

```json
{
  "storage": {
    "db_path": "~/.gmemory/data.db"
  },
  "embedding": {
    "provider": "fastembed",
    "model": "nomic",
    "dimension": 768,
    "cache_dir": "~/.gmemory/models",
    "active_profile": "nomic",
    "profiles": {
      "nomic": {
        "provider": "fastembed",
        "model": "nomic",
        "dimension": 768
      },
      "bge-small": {
        "provider": "fastembed",
        "model": "bge-small",
        "dimension": 384
      }
    }
  },
  "scanner": {
    "default_agent": "opencode"
  },
  "search": {
    "default_mode": "hybrid",
    "default_profile": "balanced",
    "default_limit": 10,
    "vector_weight": 0.7,
    "fts_weight": 0.3,
    "recency_weight": 0.0,
    "recency_window_days": 90,
    "min_score_threshold": 0.2,
    "use_tag_index": false,
    "tag_weight": 0.3
  },
  "lifecycle": {
    "retention_days": 0,
    "archive_before_purge": true,
    "auto_compact_threshold": 1000
  }
}
```

### 配置模板

| 模板 | 描述 |
|------|------|
| `default` | 通用平衡设置 |
| `minimal` | 轻量配置，较少功能 |
| `semantic-heavy` | 优先向量搜索 |
| `recent-focused` | 强时效性加权 |
| `project-isolated` | 严格项目边界 |

```bash
# 从模板生成配置
gmemory config-generate minimal -o config.json

# 初始化项目级配置
gmemory config-init --template=project-isolated
```

### 项目级配置

在项目根目录创建 `.gmemory/config.json` 以覆盖全局设置。

## 数据源适配器

可插拔架构，支持不同 Agent 日志格式：

| 适配器 | 描述 | 日志位置 |
|--------|------|----------|
| `opencode` | OpenCode 会话日志（默认） | `~/.local/share/opencode/storage` |
| `codex-cli` | OpenAI Codex CLI 日志 | `~/.codex/logs` |
| `cursor` | Cursor IDE 对话日志 | `~/.cursor/logs` |
| `aider` | Aider 聊天历史 | `.aider.chat.history.md` |

```bash
gmemory sources              # 列出适配器
gmemory detect-source <dir>  # 自动检测
```

## 架构

### 项目结构

```
gmemory/
├── ports.py                # Protocol 接口（符合 ISP）
├── container.py            # DI 容器（单例，延迟初始化）
├── errors.py               # 结构化错误码 (GMEM-XXX-NNN)
├── config.py               # 配置管理
├── models.py               # Memory、Session 数据类
├── validation.py           # 数据质量约束
│
├── cli/                    # CLI 层（基于 Click）
│   ├── core.py             # CRUD 命令
│   ├── workflow.py         # 工作流命令
│   ├── maintenance.py      # 维护命令
│   ├── export_cmds.py      # 导出命令
│   ├── config_cmds.py      # 配置命令
│   ├── quick_cmds.py       # 快捷命令
│   └── error_handler.py    # @cli_command 装饰器
│
├── commands/               # 业务逻辑层
│   ├── search.py           # 混合搜索算法
│   ├── profiles.py         # 搜索配置文件预设
│   ├── dedupe.py           # 去重策略
│   ├── export.py           # 导出为 Markdown/JSON
│   ├── lifecycle.py        # 清理、压缩、重建索引
│   ├── health.py           # 索引健康诊断
│   ├── quick.py            # 快速访问快捷方式
│   └── workflow.py         # 会话处理
│
├── storage/                # 持久化层
│   ├── database.py         # SQLite + sqlite-vec + FTS5
│   ├── embedder.py         # FastEmbed 集成
│   └── migrations.py       # Schema 版本管理
│
└── scanner/                # 数据摄入层
    ├── base.py             # ScannerRegistry 模式
    ├── adapters.py         # 数据源适配器
    └── state.py            # 增量扫描状态
```

### 接口隔离原则 (ISP)

GMemory 使用基于 Protocol 的接口，遵循接口隔离原则：

```python
# 职责单一的隔离接口
class MemoryReadPort(Protocol):    # 读操作
class MemoryWritePort(Protocol):   # 写操作  
class MemorySearchPort(Protocol):  # 搜索操作
class WorkflowPort(Protocol):      # 会话工作流
class DiagnosticsPort(Protocol):   # 统计和健康检查

# 向后兼容的组合接口
class DatabasePort(
    MemoryReadPort,
    MemoryWritePort,
    MemorySearchPort,
    WorkflowPort,
    DiagnosticsPort,
    Protocol
):
    """新代码使用特定端口，现有代码使用 DatabasePort。"""
    pass
```

### 依赖注入

```python
from gmemory.container import get_container

# 通过 DI 容器获取服务
container = get_container()
db = container.get_database()       # DatabasePort
embedder = container.get_embedder() # EmbedderPort
config = container.get_config()     # ConfigPort

# 测试：注入 Mock
container.set_database(mock_db)
container.set_embedder(mock_embedder)
```

### 错误处理

结构化错误码遵循 `GMEM-{CATEGORY}-{NUMBER}` 模式：

| 类别 | 范围 | 描述 |
|------|------|------|
| CFG | 001-099 | 配置错误 |
| EMB | 100-199 | 嵌入错误 |
| DB | 200-299 | 数据库错误 |
| SCN | 300-399 | 扫描器错误 |
| CMD | 400-499 | 命令错误 |

```python
from gmemory.errors import DatabaseError, ErrorCode

raise DatabaseError(
    code=ErrorCode.DB_MEMORY_NOT_FOUND,
    message="记忆未找到",
    details={"memory_id": "mem_123"}
)
```

## 维护

### 健康检查

```bash
gmemory health              # 标准检查
gmemory health --verbose    # 详细诊断
gmemory health --quick      # 快速状态
```

### 重建索引

```bash
gmemory reindex --target=embeddings --apply  # 模型变更后
gmemory reindex --target=fts --apply         # 重建 FTS
gmemory reindex --target=tags --apply        # 重建标签
```

### 数据库维护

```bash
gmemory compact                    # VACUUM + ANALYZE
gmemory purge --days=180 --apply   # 清理旧记忆
gmemory lifecycle-stats            # 查看统计
```

## 与同类工具对比

| 特性 | GMemory | claude-mem | memex | opencode-mem |
|------|---------|------------|-------|--------------|
| 语言 | Python | TypeScript | Rust | TypeScript |
| 存储 | SQLite + sqlite-vec | SQLite + Chroma | Tantivy + usearch | SQLite + sqlite-vec |
| 搜索 | 混合 (vec+FTS) | 混合 (vec+FTS) | BM25 + 语义 | 向量 |
| 嵌入 | 本地 (FastEmbed) | 本地/远程 | 本地（多种） | 本地 (Xenova) |
| 接口 | CLI + MCP + 本地 Web UI | Hooks + Web UI | CLI + TUI | 插件 + Web UI |
| 后台 | 无 | Worker 服务 | 可选守护进程 | 插件钩子 |

### 为什么选择 GMemory？

- **无运行时依赖**：仅需 Python + SQLite
- **无后台进程**：无需额外服务
- **离线工作**：无需网络调用
- **易于脚本化**：可与其他工具组合使用

## 范围与非目标

| 范围内 | 范围外 |
|--------|--------|
| OpenCode CLI 工具 | 云同步 / 远程存储 |
| 本地 SQLite 存储 | 外部托管数据库 |
| 本地嵌入 (FastEmbed) | 外部嵌入 API |
| 手动提炼工作流 | 自动摘要 |
| 单用户本地使用 | 多用户 / 协作 |
| 批量 CLI 操作 | 托管云服务 |
| 本地 MCP Server + 本地 Web UI | 多租户托管平台 |

## 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 快速测试
uv run pytest tests/ -q --tb=no

# 特定模块
uv run pytest tests/test_search_modes.py -v
```

## 许可证

MIT
