---
name: gmemory
description: Memory CRUD operations for gmemory including search, add, update, delete, and stats. Use PROACTIVELY when starting tasks, encountering problems, or when context about past work would be helpful. Search memories before implementing new features or debugging issues. Also use when discovering that stored knowledge is outdated or incorrect - memories should evolve with the codebase.
---

# GMemory

## Objective
Operate the memory store using CRUD commands. Memories are living knowledge that should be searched, used, and **actively maintained** as the agent learns and evolves.

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

### Memory Correction Triggers (SELF-EVOLUTION)
- "this memory is wrong"
- "this doesn't work anymore"
- "outdated information"
- "better approach found"
- "memory needs update"
- "incorrect memory"
- "fix this memory"
- "memory is stale"
- "this pattern failed"
- "learned a better way"
- "memory conflict"
- "supersede this memory"

### Proactive Search Scenarios (Agent Should Auto-Trigger)
- Before implementing a new feature → search for similar patterns
- When encountering an error → search for past solutions
- When debugging → search for related issues
- When making architecture decisions → search for past decisions
- When asked about project history → search memories
- When context seems missing → search for background
- When starting a new task → search for related work
- When refactoring → search for design decisions

### Proactive Correction Scenarios (Agent Should Auto-Trigger)
- **When a memory's solution doesn't work** → Ask: "Should I update this memory?"
- **When finding a better approach** → Ask: "Should I supersede the old memory?"
- **When library/API has changed** → Ask: "This memory may be outdated, update?"
- **When memory conflicts with current code** → Ask: "Memory seems stale, correct it?"
- **When memory is too vague to use** → Ask: "Should I enrich this memory with details?"
- **After fixing a bug caused by wrong memory** → Update the memory immediately

### CRUD Triggers
- "add memory" / "save to memory" / "remember this"
- "update memory" / "modify memory" / "correct memory"
- "delete memory" / "remove memory" / "forget this"
- "memory stats" / "how many memories"

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
gmemory recent              # Recent memories (last 7 days)
gmemory recent -d 30 -n 20  # Last 30 days
gmemory today               # Today's activity
gmemory tag python          # Browse by tag
gmemory tags                # List all tags
```

### Add
```bash
gmemory add --content "Memory content" --tags "tag1,tag2" --importance "high"
```

### Update (IMPORTANT for self-evolution)
```bash
# Update content
gmemory update "mem_id" --content "corrected content"

# Update tags
gmemory update "mem_id" --tags "new,tags"

# Full update
gmemory update "mem_id" --content "better approach: ..." --tags "updated,tags"
```

### Delete
```bash
gmemory delete "mem_id"
```

### Supersede (Replace old with new)
```bash
# When you find a better approach, supersede the old memory
# This preserves history while marking old as replaced
gmemory add --content "New better approach" --tags "..." --importance "high"
# Then mark old as superseded (if supported) or delete
```

### Stats
```bash
gmemory stats
```

## Self-Evolution Workflow

### Pattern 1: Discover & Correct
```
1. Search memory for approach
2. Try the approach
3. If it fails or is suboptimal:
   - ASK USER: "The memory about X didn't work because Y. Should I update it?"
   - If yes: gmemory update "mem_id" --content "corrected approach"
```

### Pattern 2: Learn & Improve
```
1. Complete a task successfully
2. Compare with existing memories
3. If new approach is better:
   - ASK USER: "I found a better way to do X. Save as new memory?"
   - If yes: gmemory add --content "improved approach" --tags "..."
```

### Pattern 3: Consolidate Knowledge
```
1. Notice multiple related memories
2. ASK USER: "There are 3 memories about auth. Should I consolidate them?"
3. If yes: Create comprehensive memory, mark others as superseded
```

### Pattern 4: Deprecate Outdated
```
1. Discover memory references old API/library version
2. ASK USER: "This memory uses deprecated API. Update or delete?"
3. Take appropriate action
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

### When Memory Doesn't Work
```bash
# 1. Identify the problem
# 2. Ask user about correction
# 3. Update or delete as appropriate
gmemory update "mem_id" --content "CORRECTED: original was wrong because..."
```

## JSON Output Examples

### Search Result
```json
{
  "results": [
    {"id": "mem_x", "content": "...", "tags": ["tag1"], "score": 0.89}
  ],
  "total": 1,
  "mode": "hybrid"
}
```

## Tips for Self-Evolution
- **ALWAYS search before implementing** - check if similar work exists
- **ALWAYS verify memories** - don't blindly trust, validate against current state
- **PROACTIVELY correct** - if a memory is wrong, fix it immediately
- **ASK before major changes** - confirm with user before updating/deleting
- **Prefer update over delete** - preserve history, add corrections
- **Tag consistently** - use stable technology names for better retrieval
- **Note failures** - when something doesn't work, record why
- Use `--compact` to save tokens
- When in doubt, search first - it's cheap and often saves time
