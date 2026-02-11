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

```bash
git clone https://github.com/Keeyuu/GMemory.git
cd GMemory
```

然后按 `install.md` 执行安装与 Agent 配置同步（默认目标 `opencode`）。

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
# 默认推荐：启动单进程统一服务（API + MCP + 静态前端托管）
gmemory-service

# 兼容入口（fallback，迁移期保留）
gmemory-web

# 前端开发调试（仅 dev）
cd web
npm install
npm run dev
```

运行建议：

- 默认推荐只启动 `gmemory-service`（single-process runtime）。
- 生产/测试环境可由 `gmemory-service` 直接托管 `web/dist`，避免额外前端进程。
- 前端开发调试仍建议在 `web/` 下使用 `npm run dev`（HMR 与调试体验更好）。

若需要构建静态资源供服务托管：

```bash
cd web
npm run build
```

Web 联调建议：

- 推荐主链路为 `gmemory-service`；本地前端改动时再叠加 `npm run dev`。
- 若前端已提供 `/mcp` 调试页，可直接在浏览器访问并验证 MCP 工具调用。
- 若未提供 `/mcp` 调试页，可用 `gmemory-mcp` 或 `python -m gmemory.mcp` 作为 fallback 命令行联调。

最小 PM2 示例（推荐仅单进程）：

```javascript
module.exports = {
  apps: [
    {
      name: 'gmemory-service',
      script: 'gmemory-service',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
      env: {
        NODE_ENV: 'production',
      },
    },
    // 可选：仅前端 dev 调试时启用
    // {
    //   name: 'gmemory-frontend',
    //   cwd: 'web',
    //   script: 'npm',
    //   args: 'run dev',
    // }
  ],
}
```

```bash
pm2 start ecosystem.config.js --only gmemory-service
pm2 save
```

默认：

- API：`http://127.0.0.1:8765`
- Frontend Dev：`http://127.0.0.1:5173`

## 6. MCP

```bash
# 启动统一服务（默认推荐，single-process runtime）
gmemory-service

# 启动 MCP（fallback 兼容入口，迁移期保留）
gmemory-mcp
```

推荐的 MCP 会话工作流（统一接口）：

1. 使用 `gmemory_session_list(limit=100, state="unprocessed", agent="all", scanner_type="all")` 拉取全局未处理会话。
2. 使用 `session_read(session_id=...)` 读取会话内容并提炼。
3. 使用 `gmemory_add` / `gmemory_update` 写入记忆。
4. 写入成功后使用 `gmemory_mark_session(session_id=..., agent=...)` 标记处理完成。

兼容说明：`gmemory_fetch_unprocessed` 仍可用（fallback），但建议迁移到 `gmemory_session_list`。

也可使用：

```bash
python -m gmemory.mcp
```

### Agent 配置同步（install.md）

- `opencode`（默认）：
  - 写入 `~/.config/opencode/opencode.json` 的 `mcp.gmemory`。
  - 同步 `opencode/commands/*` 与 `opencode/agents/*`。
  - 推荐执行 `python sync_prompts.py --with-config` 一次完成用户级同步。
- `none`：仅安装 Python 模块，不改 Agent 配置。

## 7. 外置数据导入（当前语义）

外置 provider 导入采用“先入队，再处理”模式：

1. Importer 负责扫描并写入未处理队列。
2. Agent 按常规流程处理（CLI: `fetch/process/save/mark`，MCP: `gmemory_session_list -> session_read -> add/update -> gmemory_mark_session`）。
3. `pending` 表示全局未处理总数（跨 agent 共享），可通过 pending/processed 观察处理进度。

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

涉及 MCP/分页语义改动时，建议执行固定回归顺序：

```bash
python -m pytest tests/test_fetch.py -q
python -m pytest tests/test_mcp.py -q
python -m pytest tests/test_service.py -q
pm2 restart gmemory-service
opencode mcp list
```

## 11. 文档入口

- 项目主页：`README.md`
- 中文说明：`README_CN.md`
- 前端说明：`web/README.md`
