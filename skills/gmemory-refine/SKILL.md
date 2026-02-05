---
name: gmemory-refine
description: Use when refining Agent history sessions into memories, processing session backlogs, or when the agent should learn from past conversations. Also triggers when there are unprocessed sessions that might contain valuable insights.
---

# GMemory Refine

## Objective
Refine Agent history sessions into reusable memories. Agent analyzes and decides what to keep, script handles I/O only.

## Trigger Phrases

### Session Processing Triggers
- "refine session"
- "distill session"
- "process unprocessed sessions"
- "save memory from session"
- "summarize session logs"
- "extract insights from session"
- "learn from past sessions"
- "review session history"
- "process backlog"
- "catch up on sessions"

### Knowledge Capture Triggers
- "save this for later"
- "remember this solution"
- "this is worth remembering"
- "store this pattern"
- "capture this insight"
- "document this decision"
- "save this approach"
- "record this learning"

### Backlog Management Triggers
- "check session backlog"
- "how many unprocessed sessions"
- "session status"
- "pending sessions"
- "unreviewed sessions"
- "sessions to process"

### Proactive Scenarios (Agent Should Consider)
- After completing a significant task → offer to save key insights
- When discovering a useful pattern → suggest saving it
- When making important decisions → prompt to document reasoning
- Periodically → check if there's a session backlog to process
- After debugging sessions → extract solutions worth remembering

## Workflow (fetch -> analyze -> save/mark)

1. **fetch** - Get unprocessed sessions
2. **analyze** - Agent reviews messages, selects reusable technical insights
3. **save** - Save memory (auto-marks session as processed)
4. **repeat** - If `has_more=true`, continue; otherwise done

## Commands

### Fetch Unprocessed Sessions
```bash
gmemory fetch --limit 5 --agent opencode

# Or use process (alias with workflow hints)
gmemory process --limit 5
```

### Save Memory (auto-marks session)
```bash
gmemory save \
  --session-id "ses_abc123" \
  --content "Technical insight about X" \
  --tags "auth,jwt" \
  --importance "high" \
  --type "solution"
```

### Mark Without Saving (no valuable info)
```bash
gmemory mark --session-id "ses_abc123"
```

### Batch Mark Multiple Sessions
```bash
gmemory mark-all --status=skipped --reason="bulk cleanup"
```

### Update Existing Memory
```bash
gmemory update "mem_id" --content "updated content" --tags "new,tags"
```

### Check Backlog Status
```bash
gmemory backlog
```

## JSON Output Examples

### Fetch Result
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

### Save Result
```json
{"memory_id": "mem_xyz", "created": true, "session_marked": true}
```

### Mark Result
```json
{"session_id": "ses_abc123", "marked": true}
```

## Loop Logic

```
while true:
    result = gmemory fetch --limit 5
    
    for session in result.sessions:
        # Agent analyzes session.messages
        if has_valuable_insight:
            gmemory save --session-id=... --content=... --tags=...
        else:
            gmemory mark --session-id=...
    
    if not result.has_more:
        break
```

## What Makes a Good Memory

### Worth Saving (HIGH VALUE)
- Solutions to tricky bugs
- Architecture decisions with reasoning
- Patterns that worked well
- Configuration that took time to figure out
- Workarounds for library quirks
- Performance optimizations
- Security considerations
- Integration patterns

### Skip (LOW VALUE)
- Routine CRUD operations
- Simple typo fixes
- Generic boilerplate
- Conversations without technical substance
- Incomplete or abandoned work

## Output Requirements

| Field | Description | Examples |
|-------|-------------|----------|
| content | Concise, reusable technical insight | "JWT refresh token rotation pattern with Redis" |
| tags | Comma-separated, stable topics | `auth,jwt,redis,cache` |
| importance | Priority level | `high`, `medium`, `low` |
| type | Memory category | `decision`, `solution`, `pattern`, `preference` |

## Tips
- Focus on **reusable** insights, not session-specific details
- Use stable tags (technology names, patterns) not ephemeral ones
- Mark sessions without value to avoid re-processing
- Use `gmemory backlog` to check progress
- **Proactively offer** to save insights after significant work
- Check backlog periodically - don't let it grow too large
