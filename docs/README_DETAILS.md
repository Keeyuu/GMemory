# GMemory 详细文档

本文档收纳详细的安装、运行、命令、配置与维护说明。`README.md` 只保留项目定位、核心卖点与截图展示。

## 1. 架构概览

GMemory 是本地优先的 agent memory system，核心由以下模块组成：

- `gmemory/scanner/*`：扫描不同来源 session 数据。
- `gmemory/commands/*`：业务命令层（search/process/save/fetch/backup/import 等）。
- `gmemory/storage/*`：SQLite、`sqlite-vec`、FTS 与 schema/migration。
- `gmemory/webapi.py`：Web API。
- `web/`：Vue3 前端。

## 2. 安装

### Windows

```powershell
git clone https://github.com/Keeyuu/GMemory.git
cd GMemory
powershell -ExecutionPolicy Bypass -File install.ps1
```

### Linux/macOS

```bash
git clone https://github.com/Keeyuu/GMemory.git
cd GMemory
chmod +x install.sh && ./install.sh
```

### 手动安装

```bash
uv pip install -e .
```

## 3. 常用工作流

```bash
# 拉取未处理会话
gmemory fetch --limit=10

# 进入处理流程
gmemory process --limit=5

# 保存记忆并标记会话
gmemory save --session-id=<id> --content="..." --preview="..." --tags="..."

# 跳过并标记已处理
gmemory mark --session-id=<id>
```

## 4. 检索

```bash
# 混合检索（默认）
gmemory search "auth pattern" --compact

# 预设 profile
gmemory search "auth pattern" --profile=recent

# 查看完整内容
gmemory get <memory-id>
```

## 5. Web 与 API

```bash
# 启动 API
gmemory-web

# 启动前端
cd web
npm install
npm run dev
```

默认：

- API：`http://127.0.0.1:8765`
- Frontend Dev：`http://127.0.0.1:5173`

## 6. MCP

```bash
gmemory-mcp
```

也可使用：

```bash
python -m gmemory.mcp
```

## 7. 外置数据导入（当前语义）

外置 provider 导入采用“先入队，再处理”模式：

1. Importer 负责扫描并写入未处理队列。
2. Agent 按常规流程 `fetch/process/save/mark` 处理。
3. 可通过 pending/processed 观察处理进度。

这保证了外置数据与本地数据在 agent 视角下使用同一处理逻辑。

## 8. 备份与恢复

- 支持配置备份路径、最大保留数量、自动备份时间。
- 支持手动创建备份与恢复。
- Web 侧提供独立备份设置页面。

## 9. 常用维护命令

```bash
gmemory diagnostics
gmemory health
gmemory reindex --target=fts --apply
gmemory compact
```

## 10. 测试

```bash
uv run pytest -q
cd web && npm run build
```

## 11. 文档入口

- 项目主页：`README.md`
- 中文说明：`README_CN.md`
- 前端说明：`web/README.md`
