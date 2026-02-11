# GMemory 安装与 Agent 集成（LLM 执行版）

本文档用于让 LLM/Agent 直接按步骤执行安装与配置，不依赖 `install.ps1` 或 `install.sh`。

默认目标 agent 为 `opencode`。可选：`none`。

## 0. 参数约定

- `AGENT_TARGET`：`opencode`（默认）/ `none`

建议在执行前先明确：

```text
AGENT_TARGET=opencode
```

## 1. 安装 Python 包

在仓库根目录执行：

```bash
# 推荐（需要 uv）
uv pip install -e .

# 备选（无 uv）
pip install -e .
```

## 2. 基础校验

```bash
gmemory --version
gmemory health
```

## 3. 启动统一服务（单进程）

```bash
gmemory-service
```

说明：

- `gmemory-service` 同时提供 API（`/api/*`）与 MCP（`/mcp/*`）。
- 若需托管前端页面，请先在 `web/` 下执行 `npm run build`，服务会读取 `web/dist`。

如果你需要保留本地 stdio fallback，可使用 `gmemory-mcp`（Windows 常见绝对路径示例）：

```text
C:\Code\GMemory\.venv\Scripts\gmemory-mcp.exe
```

## 4. 配置 MCP（按 AGENT_TARGET）

### 3.1 OpenCode（`AGENT_TARGET=opencode`）

目标文件：`~/.config/opencode/opencode.json`

写入/更新：

```json
{
  "mcp": {
    "gmemory": {
      "type": "remote",
      "url": "http://127.0.0.1:8765/mcp/",
      "enabled": true
    }
  }
}
```

可选 fallback（仅在 remote 异常时启用）：

```json
{
  "mcp": {
    "gmemory_local_fallback": {
      "command": ["<ABSOLUTE_PATH_TO_GMEMORY_MCP>"],
      "enabled": false,
      "type": "local"
    }
  }
}
```

## 5. 同步 command/subagent 提示词模板

### 4.1 OpenCode（`AGENT_TARGET=opencode`）

复制以下文件到用户级目录：

- `opencode/commands/refine-memory.md` -> `~/.config/opencode/commands/refine-memory.md`
- `opencode/commands/scan-memories.md` -> `~/.config/opencode/commands/scan-memories.md`
- `opencode/agents/knowledge-archivist.md` -> `~/.config/opencode/agents/knowledge-archivist.md`

推荐使用仓库脚本一键同步（包含 prompts，可选同步 `opencode.json`）：

```bash
# 仅同步 prompts
python sync_prompts.py

# 同步 prompts + 强制校准 mcp.gmemory 到 remote
python sync_prompts.py --with-config
```

## 6. 最终验收

### OpenCode 验收

1. 完全重启 OpenCode。
2. 检查 `gmemory` MCP 可见。
3. 运行 `scan-memories` / `refine-memory`，确认可调用 `knowledge-archivist`。

### MCP 改动后的固定回归顺序

当改动涉及 MCP 工具、分页语义、会话工作流时，统一按以下顺序验收：

```bash
# 1) 先跑目标测试
python -m pytest tests/test_fetch.py -q
python -m pytest tests/test_mcp.py -q
python -m pytest tests/test_service.py -q

# 2) 测试通过后重启服务
pm2 restart gmemory-service
pm2 status gmemory-service

# 3) 用 opencode 直连 MCP 做运行态冒烟
opencode mcp list
opencode run "请仅调用 gmemory MCP 的 gmemory_stats 工具，并返回 unprocessed_sessions、processed_sessions、total_memories 三个字段。"
opencode run "请调用 gmemory_session_list，参数: limit=10,state='unprocessed',agent='all',scanner_type='all',compact=true。返回 total_pending、returned、remaining_after_page、next_cursor。若 next_cursor 不为空，再用该 cursor 调一次并返回第二页 returned 与第一页 session_id 是否有重叠。只输出结果。"
```

## 7. 常见问题

- **MCP 启动失败**：确认 `command` 为绝对路径且可执行。
- **命令模板不生效**：确认文件已复制到用户级目录（不是仅在仓库内存在）。
