# GMemory

Local Agent Persistent Memory System for OpenCode.

## Overview

GMemory is a lightweight CLI tool that provides persistent memory for AI coding agents. It scans OpenCode session logs, enables distillation of key information, and stores memories in a local SQLite database with hybrid vector + full-text search.

**Design Philosophy**: Minimal dependencies, local-first, CLI-driven. No background services, no web UI, no cloud dependencies.

## Features

- **Hybrid Search**: Combined vector similarity (sqlite-vec) + FTS5 full-text search with weighted scoring
- **Progressive Disclosure**: `search --compact` → `get <ids>` workflow to minimize token usage
- **Local Embeddings**: FastEmbed with nomic-embed-text-v1.5 (768 dims) - no external API calls
- **Incremental Scanning**: Track file changes via content_hash/mtime/size to skip unchanged sessions
- **Privacy Protection**: `<private>` tag filtering strips sensitive content before storage
- **Memory Lifecycle**: Supersede mechanism for updating memories while preserving history
- **Recency Weighting**: Optional time-decay scoring to favor recent memories
- **Schema Migrations**: Versioned database schema with automatic migration on startup
- **Data Validation**: Field-level validation on write paths to ensure data quality
- **Diagnostics**: Built-in health checks for sqlite-vec, dimensions, and schema status

## Installation

```bash
pip install -e .
```

**Requirements**: Python 3.10+, sqlite-vec, fastembed

## Quick Start

```bash
# 1. Fetch unprocessed sessions
gmemory process --limit=5

# 2. Save distilled memory from a session
gmemory save --session-id=<id> --content="Key insight about X" --tags="python,api"

# 3. Search memories
gmemory search "authentication pattern" --compact

# 4. Get full content
gmemory get <memory-id>
```

## Commands

| Command | Description |
|---------|-------------|
| `fetch` | Get unprocessed sessions from OpenCode logs |
| `process` | Workflow entry: fetch sessions for review |
| `save` | Save distilled memory and mark session processed |
| `mark` | Mark session as processed without saving memory |
| `search` | Hybrid/vector/FTS search with filters |
| `get` | Get full memory content by ID(s) |
| `list` | Browse memories with pagination |
| `add` | Manually add a memory |
| `update` | Update existing memory |
| `delete` | Delete a memory |
| `rebuild` | Rebuild embeddings and/or FTS index |
| `diagnostics` | Show database health and configuration |
| `stats` | Show system statistics |
| `scan-runs` | List recent scan runs |
| `scan-errors` | List scan errors for manual recovery |
| `scan-errors-resolve` | Mark scan errors as resolved |

### Search Options

```bash
gmemory search "query" \
  --mode=hybrid \        # hybrid (default), vector, fts
  --compact \            # Return previews only (saves tokens)
  --recency=0.3 \        # Weight for recent memories (0.0-1.0)
  --project=/path \      # Filter by project
  --tags=python,api \    # Filter by tags
  --include-superseded   # Include replaced memories
```

## Configuration

Default configuration in `config.toml`, override with `~/.gmemory/config.toml`:

```toml
[storage]
db_path = "~/.gmemory/data.db"

[embedding]
provider = "fastembed"
model = "nomic"
dimension = 768
cache_dir = "~/.gmemory/models"

[scanner]
default_agent = "opencode"
```

## Architecture

```
gmemory/
├── commands/           # CLI command implementations
│   ├── search.py       # Hybrid search with recency weighting
│   ├── workflow.py     # process/save_batch helpers
│   └── rebuild.py      # Index rebuild utilities
├── storage/
│   ├── database.py     # SQLite + sqlite-vec + FTS5
│   ├── embedder.py     # FastEmbed integration
│   └── migrations.py   # Schema version management
├── scanner/
│   ├── base.py         # ScannerRegistry pattern
│   ├── opencode.py     # OpenCode log parser
│   └── state.py        # Incremental scan state
├── utils/
│   └── privacy.py      # <private> tag filtering
├── validation.py       # Data quality constraints
├── models.py           # Memory, Session dataclasses
├── errors.py           # Structured error codes (GMEM-XXX-NNN)
└── logging.py          # Configurable structured logging
```

## Scope & Non-Goals

GMemory is intentionally minimal. Here's what it **does** and **doesn't** do:

| In Scope | Out of Scope |
|----------|--------------|
| CLI tool for OpenCode | Web UI / Dashboard |
| Local SQLite storage | Cloud sync / Remote storage |
| Local embeddings (FastEmbed) | External embedding APIs |
| Manual distillation workflow | Automatic summarization |
| Single-user local use | Multi-user / Collaboration |
| Batch CLI operations | Background services / Daemons |
| OpenCode session scanning | MCP server / Plugin hooks |

### Why Not MCP/Hooks?

GMemory focuses on being a reliable CLI tool that agents can invoke directly. Unlike claude-mem (hooks + worker service) or opencode-mem (plugin architecture), GMemory:

- Has no runtime dependencies beyond Python + SQLite
- Requires no background processes
- Works offline without any network calls
- Can be easily scripted and composed with other tools

### Comparison with Similar Tools

| Feature | GMemory | claude-mem | memex | opencode-mem |
|---------|---------|------------|-------|--------------|
| Language | Python | TypeScript | Rust | TypeScript |
| Storage | SQLite + sqlite-vec | SQLite + Chroma | Tantivy + usearch | SQLite + sqlite-vec |
| Search | Hybrid (vec+FTS) | Hybrid (vec+FTS) | BM25 + semantic | Vector |
| Embeddings | Local (FastEmbed) | Local/Remote | Local (multiple) | Local (Xenova) |
| Interface | CLI only | Hooks + Web UI | CLI + TUI | Plugin + Web UI |
| Background | None | Worker service | Optional daemon | Plugin hooks |
| Target | OpenCode | Claude Code | Claude/Codex/OpenCode | OpenCode |

## Maintenance

### Rebuild Indexes

```bash
# After changing embedding model
gmemory rebuild --target=embeddings

# Rebuild FTS index
gmemory rebuild --target=fts

# Dry run to see what would change
gmemory rebuild --target=all --dry-run
```

### Check Health

```bash
gmemory diagnostics
```

Output includes: sqlite-vec status, dimension config, schema version, memory counts.

## License

MIT
