---
name: gmemory
description: Memory CRUD operations for gmemory including search, add, update, delete, and stats. Use PROACTIVELY when starting tasks, encountering problems, or when context about past work would be helpful. Search memories before implementing new features or debugging issues.
---

# GMemory

## Objective
Operate the memory store using CRUD commands and inspect overall stats.

## Trigger Phrases

### Search Triggers (HIGH PRIORITY - Use Proactively)
- "search memories"
- "find in memory"
- "what do I know about"
- "have I seen this before"
- "did we do this before"
- "check memory for"
- "look up in memory"
- "recall"
- "remember"
- "previous solution"
- "past experience"
- "similar problem"
- "related work"
- "existing pattern"
- "how did we handle"
- "what was the approach"
- "any notes on"
- "context about"
- "background on"
- "history of"

### Proactive Search Scenarios (Agent Should Auto-Trigger)
- Before implementing a new feature → search for similar patterns
- When encountering an error → search for past solutions
- When debugging → search for related issues
- When making architecture decisions → search for past decisions
- When asked about project history → search memories
- When context seems missing → search for background
- When starting a new task → search for related work
- When refactoring → search for design decisions

### CRUD Triggers
- "add memory"
- "save to memory"
- "remember this"
- "store this insight"
- "update memory"
- "modify memory"
- "delete memory"
- "remove memory"
- "memory stats"
- "how many memories"

## Commands

### Search
```bash
# Basic search (always use --compact first to save tokens)
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

## Recommended Workflow

### Before Starting Any Task
```bash
# 1. Quick search for related context
gmemory q "task keywords" --compact

# 2. If results found, get full content
gmemory get <memory-id>

# 3. Check recent activity in the area
gmemory recent -d 7
```

### When Encountering Problems
```bash
# 1. Search for similar issues
gmemory search "error message or symptom" --compact

# 2. Search by technology/tag
gmemory tag <technology>

# 3. Check past decisions
gmemory search "decision about X" --profile=recent
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

## Tips
- **ALWAYS search before implementing** - check if similar work exists
- Use `--compact` to save tokens (returns id, tags, preview only)
- Use `--explain` to see detailed scoring breakdown
- Use profiles instead of manual weight tuning
- Quick commands (`q`, `recent`, `today`, `tag`) are faster for common operations
- When in doubt, search first - it's cheap and often saves time
