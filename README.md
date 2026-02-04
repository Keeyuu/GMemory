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
- **Session Aggregation**: Group memories by session for efficient review and auditing
- **Search Explainability**: Detailed scoring breakdown showing vector/FTS/recency contributions
- **Dual Vector Index**: Optional tag-based semantic search for improved matching
- **Search Profiles**: Pre-configured search presets for common use cases
- **Deduplication**: Find and merge similar/duplicate memories with multiple strategies (vector, simhash, minhash)
- **Export**: Export memories and reports to Markdown or JSON
- **Data Lifecycle**: Purge, compact, and reindex commands for long-term maintenance
- **Embedding Profiles**: Multiple embedding model configurations with migration workflow
- **Index Health Check**: Comprehensive diagnostics for all database indexes
- **Quick Commands**: Shortcut commands for common high-frequency operations
- **Source Adapters**: Pluggable architecture for parsing different agent log formats

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
| `mark-all` | Batch mark multiple sessions as processed |
| `backlog` | Show session backlog status and workflow suggestions |
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
| `scan-errors-summary` | Show scan error summary with recommendations |
| `scan-errors-batch-resolve` | Batch resolve scan errors by type |
| `session-report` | Generate session-level aggregation report |
| `session-detail` | Get detailed information about a specific session |
| `profiles` | List available search profiles |
| `dedupe` | Find groups of similar/duplicate memories |
| `merge` | Merge multiple memories into one |
| `auto-dedupe` | Automatically find and merge near-duplicates |
| `session-export` | Export session memories to Markdown/JSON |
| `report-export` | Export session report to Markdown/JSON |
| `export` | Export memories by ID or filters |
| `purge` | Delete old memories based on retention policy |
| `compact` | Compact and optimize the database |
| `reindex` | Rebuild database indexes (embeddings, FTS, tags) |
| `lifecycle-stats` | Show memory age distribution and lifecycle info |
| `embedding-profiles` | List/show embedding model profiles |
| `embedding-check` | Check compatibility before switching profiles |
| `embedding-switch` | Switch to a different embedding profile |
| `index-info` | Show index version and coverage information |
| `health` | Check index health and identify issues |
| `q` | Quick search shortcut (compact mode) |
| `recent` | Show most recent memories |
| `today` | Show today's activity summary |
| `tag` | Find memories by tag |
| `tags` | List all tags with counts |
| `sources` | List available source adapters |
| `detect-source` | Detect source type from a directory |
| `config-templates` | List available configuration templates |
| `config-generate` | Generate config file from template |
| `config-init` | Initialize project-level configuration |
| `config-show` | Show current effective configuration |

### Search Options

```bash
gmemory search "query" \
  --profile=recent \     # Use preset profile (see below)
  --mode=hybrid \        # hybrid (default), vector, fts
  --compact \            # Return previews only (saves tokens)
  --recency=0.3 \        # Weight for recent memories (0.0-1.0)
  --project=/path \      # Filter by project
  --tags=python,api \    # Filter by tags
  --include-superseded \ # Include replaced memories
  --explain \            # Show detailed scoring breakdown
  --use-tag-index \      # Enable dual vector search (content + tags)
  --tag-weight=0.3 \     # Weight for tag similarity (0.0-1.0)
  --min-score=0.2        # Minimum score threshold (0.0-1.0)
```

### Search Profiles

Profiles provide pre-configured search settings for common use cases:

```bash
# List available profiles
gmemory profiles

# Show profile details
gmemory profiles recent

# Use a profile
gmemory search "authentication" --profile=recent
gmemory search "python" -p tag-heavy --explain
```

| Profile | Mode | Recency | Tags | Description |
|---------|------|---------|------|-------------|
| `balanced` | hybrid | 0.0 | - | Default balanced search (vector + FTS) |
| `semantic` | vector | 0.0 | - | Pure semantic similarity only |
| `keyword` | fts | 0.0 | - | Full-text keyword search only |
| `recent` | hybrid | 0.4 | - | Moderate recency boost |
| `very-recent` | hybrid | 0.7 | - | Strong recency boost |
| `tag-heavy` | hybrid | 0.0 | 0.6 | Prioritize tag similarity |
| `tag-only` | hybrid | 0.0 | 0.8 | Search primarily by tags |
| `fresh-tags` | hybrid | 0.3 | 0.5 | Tags + recency combined |

Individual options (--mode, --recency, etc.) override profile settings.

### Session Aggregation

```bash
# View session-level summary
gmemory session-report --limit=10 --since=7

# Get details for a specific session
gmemory session-detail <session-id>
gmemory session-detail <session-id> --full  # Include full content
```

### Deduplication

Find and merge similar/duplicate memories with multiple strategies:

```bash
# Find duplicate groups (vector similarity - default)
gmemory dedupe                          # Default threshold 0.85
gmemory dedupe --threshold=0.90         # Stricter matching
gmemory dedupe --strategy=simhash       # Use SimHash (faster, no embeddings)
gmemory dedupe --strategy=minhash       # Use MinHash (Jaccard similarity)
gmemory dedupe --project=/path          # Filter by project

# Merge specific memories
gmemory merge mem1 mem2 mem3 --dry-run   # Preview merge
gmemory merge mem1 mem2 --keep=mem2      # Keep mem2 as primary
gmemory merge mem1 mem2 mem3             # Apply merge

# Auto-dedupe (high threshold, safe)
gmemory auto-dedupe                      # Preview what would be merged
gmemory auto-dedupe --threshold=0.90     # Lower threshold
gmemory auto-dedupe --strategy=simhash   # Use SimHash
gmemory auto-dedupe --apply              # Actually merge duplicates
```

**Deduplication Strategies:**
| Strategy | Description | Use Case |
|----------|-------------|----------|
| `vector` | Semantic similarity using embeddings | Most accurate, requires embeddings |
| `simhash` | Locality-sensitive hashing | Fast, good for near-duplicates |
| `minhash` | Jaccard similarity estimation | Good for content overlap detection |

### Export

Export memories and reports to Markdown or JSON:

```bash
# Export session memories
gmemory session-export ses_abc123
gmemory session-export ses_abc123 --format=json
gmemory session-export ses_abc123 -o session.md

# Export session report
gmemory report-export
gmemory report-export --format=json --since=7
gmemory report-export -o report.md --limit=50

# Export specific memories
gmemory export mem1 mem2 mem3
gmemory export --project=/path --format=json
gmemory export --tags=python,api -o export.md
```

### Data Lifecycle Management

Manage database size and performance over time:

```bash
# Purge old memories (dry-run by default)
gmemory purge --days=90              # Preview purge of memories > 90 days
gmemory purge --days=90 --apply      # Actually purge
gmemory purge --apply --no-archive   # Purge without archiving

# Compact database
gmemory compact                      # Full compaction (VACUUM + ANALYZE)
gmemory compact --no-vacuum          # Only analyze, skip vacuum
gmemory compact --rebuild-fts        # Also rebuild FTS index

# Reindex (dry-run by default)
gmemory reindex                      # Preview all reindex
gmemory reindex --target=embeddings  # Preview embedding rebuild
gmemory reindex --target=fts --apply # Rebuild FTS index
gmemory reindex --apply              # Rebuild everything

# View lifecycle statistics
gmemory lifecycle-stats              # Memory age distribution, DB size
```

### Embedding Profiles

Manage multiple embedding model configurations:

```bash
# List available profiles
gmemory embedding-profiles

# Show profile details
gmemory embedding-profiles nomic

# Check compatibility before switching
gmemory embedding-check bge-small

# Switch profile (dry-run by default)
gmemory embedding-switch bge-small              # Preview switch
gmemory embedding-switch bge-small --apply      # Switch (runtime only)
gmemory embedding-switch bge-small --apply --rebuild  # Switch and rebuild

# View index version info
gmemory index-info
```

### Index Health Check

Monitor and diagnose index issues:

```bash
# Standard health check
gmemory health

# Detailed diagnostics
gmemory health --verbose

# Quick check (faster)
gmemory health --quick
```

### Quick Commands

Shortcut commands for common operations:

```bash
# Quick search (compact mode)
gmemory q "authentication"
gmemory q "api design" -n 10
gmemory q "error handling" -d 7    # Boost recent

# Recent memories
gmemory recent                     # Last 7 days
gmemory recent -d 30               # Last 30 days
gmemory recent -d 1 -n 20          # Last 24 hours

# Today's summary
gmemory today

# Browse by tag
gmemory tag python
gmemory tag api -n 50
gmemory tags                       # List all tags with counts
```

### Source Adapters

Pluggable architecture for different agent log formats:

```bash
# List available adapters
gmemory sources

# Show adapter details
gmemory sources opencode

# Detect source type from directory
gmemory detect-source ~/.local/share/opencode/storage
```

**Available Adapters:**

| Adapter | Description | Log Location |
|---------|-------------|--------------|
| `opencode` | OpenCode session logs (default) | `~/.local/share/opencode/storage` |
| `codex-cli` | OpenAI Codex CLI logs | `~/.codex/logs` |
| `cursor` | Cursor IDE conversation logs | `~/.cursor/logs` |
| `aider` | Aider chat history | `.aider.chat.history.md` |

Each adapter handles the specific log format and extracts session metadata for processing.

### Configuration Templates

Pre-configured templates for different use cases:

```bash
# List available templates
gmemory config-templates

# Generate config from template
gmemory config-generate minimal -o config.toml
gmemory config-generate semantic-heavy  # Output to stdout

# Initialize project-level config
gmemory config-init                     # Uses 'default' template
gmemory config-init --template=project-isolated

# Show current effective configuration
gmemory config-show
gmemory config-show --section=search    # Show specific section
```

**Available Templates:**

| Template | Description |
|----------|-------------|
| `default` | Balanced settings for general use |
| `minimal` | Lightweight config, fewer features enabled |
| `semantic-heavy` | Prioritize vector search over FTS |
| `recent-focused` | Strong recency weighting for fresh memories |
| `project-isolated` | Strict project boundaries, no cross-project search |

**Project-Level Configuration:**

Create `.gmemory/config.toml` in your project root to override global settings:

```bash
cd /path/to/project
gmemory config-init --template=project-isolated
# Creates .gmemory/config.toml with project-specific settings
```

### Batch Workflow Commands

Efficiently manage session backlogs:

```bash
# View backlog status and recommendations
gmemory backlog

# Batch mark sessions as processed
gmemory mark-all --status=skipped --reason="bulk cleanup"
gmemory mark-all --before=2024-01-01 --status=skipped

# Scan error management
gmemory scan-errors-summary              # View error summary with suggestions
gmemory scan-errors-batch-resolve --type=parse_error --action=skip
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
active_profile = "nomic"

[embedding.profiles.nomic]
provider = "fastembed"
model = "nomic"
dimension = 768

[embedding.profiles.bge-small]
provider = "fastembed"
model = "bge-small"
dimension = 384

[scanner]
default_agent = "opencode"

[search]
default_mode = "hybrid"
default_profile = "balanced"
default_limit = 10
vector_weight = 0.7
fts_weight = 0.3
recency_weight = 0.0
recency_window_days = 90
min_score_threshold = 0.2
use_tag_index = false
tag_weight = 0.3

[lifecycle]
retention_days = 0          # 0 = no auto-purge
archive_before_purge = true
auto_compact_threshold = 1000
```

## Architecture

```
gmemory/
├── cli/                    # Modular CLI command groups
│   ├── __init__.py         # CLI entry point and registration
│   ├── core.py             # Core CRUD commands (fetch, save, search, get, list, add, update, delete, stats)
│   ├── workflow.py         # Workflow commands (process, mark-all, backlog, scan-*, session-*)
│   ├── maintenance.py      # Maintenance commands (rebuild, diagnostics, health, purge, compact, reindex)
│   ├── export_cmds.py      # Export commands (session-export, report-export, export)
│   ├── config_cmds.py      # Configuration commands (config-templates, config-generate, config-init, config-show)
│   ├── quick_cmds.py       # Quick shortcuts (q, recent, today, tag, tags)
│   └── adapters_cmds.py    # Adapter commands (sources, detect-source)
├── commands/               # Command business logic
│   ├── search.py           # Hybrid search with recency weighting
│   ├── profiles.py         # Search profile presets
│   ├── dedupe.py           # Deduplication (vector/simhash/minhash)
│   ├── export.py           # Export to Markdown/JSON
│   ├── lifecycle.py        # Purge, compact, reindex commands
│   ├── embedding_profiles.py # Embedding model management
│   ├── health.py           # Index health diagnostics
│   ├── quick.py            # Quick access shortcuts
│   ├── workflow.py         # process/save_batch/backlog helpers
│   └── rebuild.py          # Index rebuild utilities
├── storage/
│   ├── database.py         # SQLite + sqlite-vec + FTS5
│   ├── embedder.py         # FastEmbed integration
│   └── migrations.py       # Schema version management
├── scanner/
│   ├── base.py             # ScannerRegistry pattern
│   ├── opencode.py         # OpenCode log parser
│   ├── adapters.py         # Source adapters (OpenCode, Codex, Cursor, Aider)
│   └── state.py            # Incremental scan state
├── utils/
│   └── privacy.py          # <private> tag filtering
├── validation.py           # Data quality constraints
├── models.py               # Memory, Session dataclasses
├── config.py               # Configuration management with templates
├── errors.py               # Structured error codes (GMEM-XXX-NNN)
└── logging.py              # Configurable structured logging
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
gmemory reindex --target=embeddings --apply

# Rebuild FTS index
gmemory reindex --target=fts --apply

# Rebuild tag index
gmemory reindex --target=tags --apply

# Dry run to see what would change
gmemory reindex --target=all
```

### Check Health

```bash
# Comprehensive health check
gmemory health

# Detailed diagnostics
gmemory health --verbose

# Quick status check
gmemory health --quick

# Legacy diagnostics command
gmemory diagnostics
```

Output includes: sqlite-vec status, dimension config, schema version, memory counts, index coverage, and recommendations.

### Database Maintenance

```bash
# Compact database (reclaim space)
gmemory compact

# Purge old memories
gmemory purge --days=180 --apply

# View lifecycle statistics
gmemory lifecycle-stats
```

## License

MIT
