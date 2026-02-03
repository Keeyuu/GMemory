---
name: gmemory
description: Memory CRUD operations for gmemory including search, add, update, delete, and stats.
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

## Commands
```bash
# search
python -m gmemory search "query" [--project PATH] [--tags "a,b"] [--limit 5]

# add
python -m gmemory add --content "Memory content" --tags "tag1,tag2" --importance "high"

# update
python -m gmemory update "mem_id" [--content "new"] [--tags "new,tags"]

# delete
python -m gmemory delete "mem_id"

# stats
python -m gmemory stats
```

## JSON output examples
```json
{"results": [{"id": "mem_x", "content": "...", "tags": ["tag1"], "similarity": 0.89}], "total": 1}
```

```json
{"id": "mem_xyz", "created": true}
```

```json
{"id": "mem_id", "updated": true}
```

```json
{"id": "mem_id", "deleted": true}
```

```json
{"total_memories": 42, "unprocessed_sessions": 5, "by_project": {"/path": 10}, "by_importance": {"high": 3, "medium": 30, "low": 9}}
```
