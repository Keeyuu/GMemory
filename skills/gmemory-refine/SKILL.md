---
name: gmemory-refine
description: Use when refining Agent history sessions into memories, needing fetch/save/mark loop, or when asked to distill sessions, summarize logs, or process unprocessed sessions for gmemory.
---

# GMemory Refine

## 目标
将 Agent 历史会话提炼为可复用记忆，由 Agent 负责分析与取舍，脚本只做 I/O。

## 触发短语
- "refine session"
- "distill session"
- "提炼会话"
- "整理对话要点"
- "处理未处理会话"
- "save memory from session"

## 工作流 (fetch -> analyze -> save/mark)
1) fetch 获取未处理会话
2) Agent 分析 messages，选择可复用技术要点
3) save 保存记忆 (会自动标记 session)
4) 若 has_more 为 true，继续下一轮；否则结束

## 命令
```bash
# fetch
python -m gmemory fetch --limit 5 --agent opencode

# save (保存后自动标记)
python -m gmemory save --session-id "ses_abc123" --content "技术要点" --tags "auth,jwt" --importance "high" --type "solution"
# 修改记忆
python -m gmemory update "mem_id" [--content "new"] [--tags "new,tags"]

# mark (仅标记，不保存, 无有价值信息)
python -m gmemory mark --session-id "ses_abc123"
```

## JSON 输出示例
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

```json
{"memory_id": "mem_xyz", "created": true, "session_marked": true}
```

```json
{"session_id": "ses_abc123", "marked": true}
```

## has_more 循环逻辑
- has_more=true: 继续 fetch 下一批，直到 has_more=false
- remaining 仅作提示，不应替代 has_more
- 若不需要保存记忆，可用 mark 直接标记该 session

## 产出要求
- content: 简洁、可复用的技术要点
- tags: 逗号分隔，偏向稳定主题 (auth,jwt,cache)
- importance: high/medium/low
- type: decision/solution/pattern/preference
