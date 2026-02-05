---
name: gmemory
description: Memory CRUD operations for gmemory including search, add, update, delete, and stats. Use when user asks to search memories, add memory, update memory, delete memory, or check memory stats.
---

# GMemory

## Objective
Operate the memory store using CRUD commands and inspect overall stats.

## Trigger phrases
- "search memories"
- "add memory"
- "update memory"
- "delete memory"
- "memory stats"
- "find in memory"
- "what do I know about"

## Commands

### Search
```bash
# Basic search
gmemory search "query" --compact

# With filters
gmemory search "query" --project /path --tags "tag1,tag2" --limit 10

# With profile preset
gmemory search "query" --profile recent --explain

# Quick search shortcut
gmemory q "query"
```

### Quick Commands
```bash
# Recent memories (last 7 days)
gmemory recent
gmemory recent -d 30 -n 20

# Today's activity
gmemory today

# Browse by tag
gmemory tag python
gmemory tags  # List all tags
```

### Add
```bash
gmemory add --content "Memory content" --tags "tag1,tag2" --importance "high"
```

### Update
```bash
gmemory update "mem_id" --content "new content" --tags "new,tags"
```

### Delete
```bash
gmemory delete "mem_id"
```

### Stats
```bash
gmemory stats
```

## Search Profiles
Available presets: `balanced`, `semantic`, `keyword`, `recent`, `very-recent`, `tag-heavy`, `tag-only`, `fresh-tags`

```bash
gmemory search "auth" --profile=recent      # Favor recent memories
gmemory search "api" --profile=semantic     # Pure vector search
gmemory search "error" --profile=keyword    # Full-text only
```

## JSON Output Examples

### Search Result
```json
{
  "results": [
    {"id": "mem_x", "content": "...", "tags": ["tag1"], "score": 0.89}
  ],
  "total": 1,
  "mode": "hybrid",
  "profile": "balanced"
}
```

### Add Result
```json
{"id": "mem_xyz", "created": true}
```

### Update Result
```json
{"id": "mem_id", "updated": true}
```

### Delete Result
```json
{"id": "mem_id", "deleted": true}
```

### Stats Result
```json
{
  "total_memories": 42,
  "unprocessed_sessions": 5,
  "by_project": {"/path": 10},
  "by_importance": {"high": 3, "medium": 30, "low": 9}
}
```

## Tips
- Use `--compact` to save tokens (returns id, tags, preview only)
- Use `--explain` to see detailed scoring breakdown
- Use profiles instead of manual weight tuning
- Quick commands (`q`, `recent`, `today`, `tag`) are faster for common operations
