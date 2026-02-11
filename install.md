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
gmemory-mcp --help
gmemory health
```

如果 `gmemory-mcp` 不在 PATH，请使用仓库虚拟环境中的绝对路径（Windows 常见）：

```text
C:\Code\GMemory\.venv\Scripts\gmemory-mcp.exe
```

## 3. 配置 MCP（按 AGENT_TARGET）

### 3.1 OpenCode（`AGENT_TARGET=opencode`）

目标文件：`~/.config/opencode/opencode.json`

写入/更新：

```json
{
  "mcp": {
    "gmemory": {
      "command": ["<ABSOLUTE_PATH_TO_GMEMORY_MCP>"],
      "enabled": true,
      "type": "local"
    }
  }
}
```

## 4. 同步 command/subagent 提示词模板

### 4.1 OpenCode（`AGENT_TARGET=opencode`）

复制以下文件到用户级目录：

- `opencode/commands/refine-memory.md` -> `~/.config/opencode/commands/refine-memory.md`
- `opencode/commands/scan-memories.md` -> `~/.config/opencode/commands/scan-memories.md`
- `opencode/agents/knowledge-archivist.md` -> `~/.config/opencode/agents/knowledge-archivist.md`

## 5. 最终验收

### OpenCode 验收

1. 完全重启 OpenCode。
2. 检查 `gmemory` MCP 可见。
3. 运行 `scan-memories` / `refine-memory`，确认可调用 `knowledge-archivist`。

## 6. 常见问题

- **MCP 启动失败**：确认 `command` 为绝对路径且可执行。
- **命令模板不生效**：确认文件已复制到用户级目录（不是仅在仓库内存在）。
