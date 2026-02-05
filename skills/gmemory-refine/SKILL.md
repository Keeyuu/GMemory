---
name: gmemory-refine
description: Use when refining Agent history sessions into memories, processing session backlogs, maintaining memory quality, or when the agent should learn from past conversations. Triggers on session processing, knowledge capture, and memory evolution activities. The agent should proactively suggest saving valuable insights and correcting outdated memories.
---

# GMemory Refine

## Objective
Refine Agent history sessions into reusable memories AND maintain memory quality over time. This is the agent's self-evolution mechanism - learning from experience and keeping knowledge current.

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
- "this worked well"
- "important discovery"

### Memory Evolution Triggers (SELF-IMPROVEMENT)
- "this memory is outdated"
- "better approach discovered"
- "memory needs correction"
- "update existing knowledge"
- "consolidate memories"
- "clean up memories"
- "memory quality check"
- "review memory accuracy"
- "deprecate old pattern"
- "learned from mistake"

### Backlog Management Triggers
- "check session backlog"
- "how many unprocessed sessions"
- "session status"
- "pending sessions"
- "unreviewed sessions"
- "sessions to process"

### Proactive Scenarios (Agent Should Auto-Trigger)

#### Knowledge Capture
- After completing a significant task → **ASK**: "Should I save the key insights from this?"
- When discovering a useful pattern → **ASK**: "This pattern worked well. Save it?"
- When making important decisions → **ASK**: "Document the reasoning for this decision?"
- After debugging a tricky issue → **ASK**: "Save this solution for future reference?"
- When finding a workaround → **ASK**: "This workaround might be useful later. Remember it?"

#### Memory Maintenance
- When a saved approach fails → **ASK**: "This memory didn't work. Update or delete it?"
- When finding conflicting memories → **ASK**: "These memories conflict. Consolidate them?"
- When memory references old API → **ASK**: "This memory uses deprecated API. Update?"
- Periodically → **SUGGEST**: "There are X unprocessed sessions. Process them?"
- When memory is too vague → **ASK**: "This memory lacks detail. Enrich it?"

#### Self-Reflection
- After a failed attempt → **LEARN**: "What went wrong? Should I update related memories?"
- After success with new approach → **COMPARE**: "Is this better than what's in memory?"
- When user corrects agent → **CAPTURE**: "Should I remember this correction?"

## Workflow (fetch -> analyze -> save/mark)

1. **fetch** - Get unprocessed sessions
2. **analyze** - Agent reviews messages, selects reusable technical insights
3. **save** - Save memory (auto-marks session as processed)
4. **repeat** - If `has_more=true`, continue; otherwise done

### Batch Skip Guardrail
- Batch skip MUST include a non-empty reason and requires `--apply`.
- If skipping without saving, prefer `mark` with `--status=skipped --reason=...`.

## Commands

### Fetch Unprocessed Sessions
```bash
gmemory fetch --limit 5 --agent opencode
gmemory process --limit 5  # Alias with workflow hints
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
gmemory mark --session-id "ses_abc123" --status=skipped --reason="no reusable insight"
```

### Batch Mark Multiple Sessions
```bash
gmemory mark-all --reason="bulk cleanup" --apply
```

### Update Existing Memory (CRITICAL for evolution)
```bash
# Correct an error
gmemory update "mem_id" --content "CORRECTED: The right approach is..."

# Add missing details
gmemory update "mem_id" --content "Original content + Additional context: ..."

# Update tags for better discovery
gmemory update "mem_id" --tags "corrected,updated,auth"
```

### Check Backlog Status
```bash
gmemory backlog
```

## Memory Evolution Patterns

### Pattern 1: Correct on Failure
```
Scenario: Used a memory's approach, but it failed

1. Identify why it failed
2. ASK USER: "The memory about [topic] failed because [reason]. Should I:
   a) Update with the correct approach
   b) Delete it
   c) Keep as-is with a warning note"
3. Execute user's choice
```

### Pattern 2: Upgrade on Discovery
```
Scenario: Found a better way than what's in memory

1. Compare approaches
2. ASK USER: "I found a better approach for [topic]:
   - Old: [summary]
   - New: [summary]
   Should I update the memory?"
3. If yes, update with improved content
```

### Pattern 3: Consolidate Related
```
Scenario: Multiple memories about same topic

1. Identify related memories
2. ASK USER: "Found 3 memories about [topic]. Consolidate into one comprehensive memory?"
3. If yes:
   - Create new comprehensive memory
   - Mark old ones as superseded or delete
```

### Pattern 4: Deprecate Outdated
```
Scenario: Memory references old version/API

1. Detect version mismatch
2. ASK USER: "Memory references [old version]. Current is [new version]. Update?"
3. Update with current information
```

### Pattern 5: Learn from Correction
```
Scenario: User corrects the agent

1. Recognize correction
2. ASK USER: "You corrected me about [topic]. Should I save this for future reference?"
3. If yes, create memory capturing the correct approach
```

## What Makes a Good Memory

### Worth Saving (HIGH VALUE)
- Solutions to tricky bugs (with root cause)
- Architecture decisions (with reasoning)
- Patterns that worked well (with context)
- Configuration that took time to figure out
- Workarounds for library quirks
- Performance optimizations (with metrics)
- Security considerations
- Integration patterns
- **Corrections to previous mistakes**
- **Lessons learned from failures**

### Worth Updating
- Approaches that partially worked (add what was missing)
- Outdated API references
- Incomplete explanations
- Memories that caused confusion

### Worth Deleting
- Completely wrong information
- Superseded by better memories
- No longer relevant (deprecated tech)
- Too vague to be useful

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
| type | Memory category | `decision`, `solution`, `pattern`, `preference`, `correction`, `lesson` |

## Self-Evolution Best Practices

1. **Search before creating** - Avoid duplicates, find related memories
2. **Verify before trusting** - Test memory's approach before relying on it
3. **Update immediately on failure** - Don't let wrong memories persist
4. **Ask before major changes** - Confirm with user for updates/deletes
5. **Preserve context** - Include WHY something works, not just WHAT
6. **Tag for discovery** - Use consistent, searchable tags
7. **Note limitations** - Record when/where approach applies
8. **Learn from mistakes** - Failures are valuable learning opportunities
9. **Consolidate periodically** - Keep memory store clean and useful
10. **Proactively suggest** - Don't wait to be asked, offer to save/update
11. **Never batch skip without reason** - Use mark-all only with explicit reason and --apply

## Tips
- Focus on **reusable** insights, not session-specific details
- Use stable tags (technology names, patterns) not ephemeral ones
- Mark sessions without value to avoid re-processing (always include reason)
- Use `gmemory backlog` to check progress
- **Proactively offer** to save insights after significant work
- **Proactively ask** about corrections when memories fail
- Check backlog periodically - don't let it grow too large
- Memories are living documents - they should evolve with the codebase
