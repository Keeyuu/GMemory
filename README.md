# GMemory

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-136%20passed-brightgreen.svg)]()

**Local Agent Persistent Memory System for OpenCode**

[中文文档](README_CN.md)

## Overview

GMemory is a lightweight CLI tool that provides persistent memory for AI coding agents. It scans OpenCode session logs, enables distillation of key information, and stores memories in a local SQLite database with hybrid vector + full-text search.

**Design Philosophy**: Minimal dependencies, local-first, CLI-driven. No background services, no web UI, no cloud dependencies.

## Features

### Core Capabilities
- **Hybrid Search**: Combined vector similarity (sqlite-vec) + FTS5 full-text search with weighted scoring
- **Progressive Disclosure**: `search --compact` → `get <ids>` workflow to minimize token usage
- **Local Embeddings**: FastEmbed with nomic-embed-text-v1.5 (768 dims) - no external API calls
- **Incremental Scanning**: Track file changes via content_hash/mtime/size to skip unchanged sessions

### Data Management
- **Privacy Protection**: `<private>` tag filtering strips sensitive content before storage
- **Memory Lifecycle**: Supersede mechanism for updating memories while preserving history
- **Deduplication**: Find and merge similar/duplicate memories (vector, simhash, minhash)
- **Data Lifecycle**: Purge, compact, and reindex commands for long-term maintenance

### Search & Discovery
- **Recency Weighting**: Optional time-decay scoring to favor recent memories
- **Search Explainability**: Detailed scoring breakdown showing vector/FTS/recency contributions
- **Dual Vector Index**: Optional tag-based semantic search for improved matching
- **Search Profiles**: Pre-configured search presets for common use cases

### Operations
- **Schema Migrations**: Versioned database schema with automatic migration on startup
- **Data Validation**: Field-level validation on write paths to ensure data quality
- **Diagnostics**: Built-in health checks for sqlite-vec, dimensions, and schema status
- **Export**: Export memories and reports to Markdown or JSON

### Extensibility
- **Embedding Profiles**: Multiple embedding model configurations with migration workflow
- **Source Adapters**: Pluggable architecture for parsing different agent log formats
- **Quick Commands**: Shortcut commands for common high-frequency operations

## Installation

### Quick Install (Recommended)

**Windows (PowerShell):**
```powershell
git clone https://github.com/Keeyuu/GMemory.git
cd GMemory
powershell -ExecutionPolicy Bypass -File install.ps1

# Skip Python module installation
powershell -ExecutionPolicy Bypass -File install.ps1 -SkipModules

# Skip skills installation
powershell -ExecutionPolicy Bypass -File install.ps1 -SkipSkills
```

**Linux/macOS:**
```bash
git clone https://github.com/Keeyuu/GMemory.git
cd GMemory
chmod +x install.sh && ./install.sh

# Skip Python module installation
./install.sh --skip-modules

# Skip skills installation
./install.sh --skip-skills
```

The install script will:
1. Install GMemory package (can be skipped)
2. Install OpenCode skills (can be skipped)
3. Create data directory `~/.gmemory/`

### Manual Install

```bash
# From source
pip install -e .

# Or with uv (recommended)
uv pip install -e .

# Install skills manually (optional)
cp -r skills/* ~/.config/opencode/skills/
```

### Install Options

| Option | Description |
|--------|-------------|
| `--dev` | Install with dev dependencies (pytest, mypy) |
| `--force` | Force reinstall (uninstall first, then install) |
| `--skip-modules` | Skip Python module installation |
| `--skip-skills` | Skip OpenCode skills installation |
| `--skills-dir <path>` | Custom skills directory |

**Upgrade**: Simply re-run the install script to upgrade to the latest version.

### Skills Installation (npx skills users)

If you manage skills via `npx skills` CLI (for OpenCode, GitHub Copilot, etc.):

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File install-skills.ps1
```

**Linux/macOS:**
```bash
chmod +x install-skills.sh && ./install-skills.sh
```

**Options:**
```bash
# Install for specific agents
./install-skills.sh --agents opencode,github-copilot

# Custom skills source directory
./install-skills.sh --skills-dir /path/to/skills

# List available skills
./install-skills.sh --list

# Uninstall skills
./install-skills.sh --uninstall
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

## Commands Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `fetch` | Get unprocessed sessions from OpenCode logs |
| `process` | Workflow entry: fetch sessions for review |
| `save` | Save distilled memory and mark session processed |
| `search` | Hybrid/vector/FTS search with filters |
| `get` | Get full memory content by ID(s) |
| `list` | Browse memories with pagination |
| `add` | Manually add a memory |
| `update` | Update existing memory |
| `delete` | Delete a memory |
| `stats` | Show system statistics |

### Workflow Commands

| Command | Description |
|---------|-------------|
| `mark` | Mark session as processed without saving memory |
| `mark-all` | Batch mark multiple sessions as processed |
| `backlog` | Show session backlog status and workflow suggestions |
| `session-report` | Generate session-level aggregation report |
| `session-detail` | Get detailed information about a specific session |

### Search & Discovery

| Command | Description |
|---------|-------------|
| `profiles` | List available search profiles |
| `q` | Quick search shortcut (compact mode) |
| `recent` | Show most recent memories |
| `today` | Show today's activity summary |
| `tag` | Find memories by tag |
| `tags` | List all tags with counts |

### Deduplication & Export

| Command | Description |
|---------|-------------|
| `dedupe` | Find groups of similar/duplicate memories |
| `merge` | Merge multiple memories into one |
| `auto-dedupe` | Automatically find and merge near-duplicates |
| `session-export` | Export session memories to Markdown/JSON |
| `report-export` | Export session report to Markdown/JSON |
| `export` | Export memories by ID or filters |

### Maintenance

| Command | Description |
|---------|-------------|
| `rebuild` | Rebuild embeddings and/or FTS index |
| `diagnostics` | Show database health and configuration |
| `health` | Check index health and identify issues |
| `purge` | Delete old memories based on retention policy |
| `compact` | Compact and optimize the database |
| `reindex` | Rebuild database indexes (embeddings, FTS, tags) |
| `lifecycle-stats` | Show memory age distribution and lifecycle info |

### Configuration

| Command | Description |
|---------|-------------|
| `config-templates` | List available configuration templates |
| `config-generate` | Generate config file from template |
| `config-init` | Initialize project-level configuration |
| `config-show` | Show current effective configuration |
| `embedding-profiles` | List/show embedding model profiles |
| `embedding-check` | Check compatibility before switching profiles |
| `embedding-switch` | Switch to a different embedding profile |

### Error Management

| Command | Description |
|---------|-------------|
| `scan-runs` | List recent scan runs |
| `scan-errors` | List scan errors for manual recovery |
| `scan-errors-resolve` | Mark scan errors as resolved |
| `scan-errors-summary` | Show scan error summary with recommendations |
| `scan-errors-batch-resolve` | Batch resolve scan errors by type |

## Search

### Search Options

```bash
gmemory search "query" \
  --profile=recent \        # Use preset profile
  --mode=hybrid \           # hybrid (default), vector, fts
  --compact \               # Return previews only (saves tokens)
  --recency=0.3 \           # Weight for recent memories (0.0-1.0)
  --project=/path \         # Filter by project
  --tags=python,api \       # Filter by tags
  --include-superseded \    # Include replaced memories
  --explain \               # Show detailed scoring breakdown
  --use-tag-index \         # Enable dual vector search
  --tag-weight=0.3 \        # Weight for tag similarity (0.0-1.0)
  --min-score=0.2           # Minimum score threshold (0.0-1.0)
```

### Search Profiles

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

```bash
# List available profiles
gmemory profiles

# Use a profile
gmemory search "authentication" --profile=recent
```

### Quick Commands

```bash
# Quick search (compact mode)
gmemory q "authentication"
gmemory q "api design" -n 10

# Recent memories
gmemory recent              # Last 7 days
gmemory recent -d 30        # Last 30 days

# Today's summary
gmemory today

# Browse by tag
gmemory tag python
gmemory tags                # List all tags
```

## Deduplication

Find and merge similar/duplicate memories:

```bash
# Find duplicate groups
gmemory dedupe                          # Default threshold 0.85
gmemory dedupe --threshold=0.90         # Stricter matching
gmemory dedupe --strategy=simhash       # Use SimHash (faster)
gmemory dedupe --strategy=minhash       # Use MinHash

# Merge memories
gmemory merge mem1 mem2 mem3 --dry-run  # Preview
gmemory merge mem1 mem2 --keep=mem2     # Keep mem2 as primary

# Auto-dedupe
gmemory auto-dedupe                     # Preview
gmemory auto-dedupe --apply             # Execute
```

**Strategies:**

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `vector` | Semantic similarity using embeddings | Most accurate |
| `simhash` | Locality-sensitive hashing | Fast, near-duplicates |
| `minhash` | Jaccard similarity estimation | Content overlap |

## Configuration

### Config File

Default: `~/.gmemory/config.json`

```json
{
  "storage": {
    "db_path": "~/.gmemory/data.db"
  },
  "embedding": {
    "provider": "fastembed",
    "model": "nomic",
    "dimension": 768,
    "cache_dir": "~/.gmemory/models",
    "active_profile": "nomic",
    "profiles": {
      "nomic": {
        "provider": "fastembed",
        "model": "nomic",
        "dimension": 768
      },
      "bge-small": {
        "provider": "fastembed",
        "model": "bge-small",
        "dimension": 384
      }
    }
  },
  "scanner": {
    "default_agent": "opencode"
  },
  "search": {
    "default_mode": "hybrid",
    "default_profile": "balanced",
    "default_limit": 10,
    "vector_weight": 0.7,
    "fts_weight": 0.3,
    "recency_weight": 0.0,
    "recency_window_days": 90,
    "min_score_threshold": 0.2,
    "use_tag_index": false,
    "tag_weight": 0.3
  },
  "lifecycle": {
    "retention_days": 0,
    "archive_before_purge": true,
    "auto_compact_threshold": 1000
  }
}
```

### Configuration Templates

| Template | Description |
|----------|-------------|
| `default` | Balanced settings for general use |
| `minimal` | Lightweight config, fewer features |
| `semantic-heavy` | Prioritize vector search over FTS |
| `recent-focused` | Strong recency weighting |
| `project-isolated` | Strict project boundaries |

```bash
# Generate config from template
gmemory config-generate minimal -o config.json

# Initialize project-level config
gmemory config-init --template=project-isolated
```

### Project-Level Configuration

Create `.gmemory/config.json` in your project root to override global settings.

## Source Adapters

Pluggable architecture for different agent log formats:

| Adapter | Description | Log Location |
|---------|-------------|--------------|
| `opencode` | OpenCode session logs (default) | `~/.local/share/opencode/storage` |
| `codex-cli` | OpenAI Codex CLI logs | `~/.codex/logs` |
| `cursor` | Cursor IDE conversation logs | `~/.cursor/logs` |
| `aider` | Aider chat history | `.aider.chat.history.md` |

```bash
gmemory sources              # List adapters
gmemory detect-source <dir>  # Auto-detect
```

## Architecture

### Project Structure

```
gmemory/
├── ports.py                # Protocol interfaces (ISP-compliant)
├── container.py            # DI container (singleton, lazy init)
├── errors.py               # Structured error codes (GMEM-XXX-NNN)
├── config.py               # Configuration management
├── models.py               # Memory, Session dataclasses
├── validation.py           # Data quality constraints
│
├── cli/                    # CLI layer (Click-based)
│   ├── core.py             # CRUD commands
│   ├── workflow.py         # Workflow commands
│   ├── maintenance.py      # Maintenance commands
│   ├── export_cmds.py      # Export commands
│   ├── config_cmds.py      # Config commands
│   ├── quick_cmds.py       # Quick shortcuts
│   └── error_handler.py    # @cli_command decorator
│
├── commands/               # Business logic layer
│   ├── search.py           # Hybrid search algorithm
│   ├── profiles.py         # Search profile presets
│   ├── dedupe.py           # Deduplication strategies
│   ├── export.py           # Export to Markdown/JSON
│   ├── lifecycle.py        # Purge, compact, reindex
│   ├── health.py           # Index health diagnostics
│   ├── quick.py            # Quick access shortcuts
│   └── workflow.py         # Session processing
│
├── storage/                # Persistence layer
│   ├── database.py         # SQLite + sqlite-vec + FTS5
│   ├── embedder.py         # FastEmbed integration
│   └── migrations.py       # Schema versioning
│
└── scanner/                # Data ingestion layer
    ├── base.py             # ScannerRegistry pattern
    ├── adapters.py         # Source adapters
    └── state.py            # Incremental scan state
```

### Interface Segregation (ISP)

GMemory uses Protocol-based interfaces following the Interface Segregation Principle:

```python
# Segregated interfaces for specific responsibilities
class MemoryReadPort(Protocol):    # Read operations
class MemoryWritePort(Protocol):   # Write operations  
class MemorySearchPort(Protocol):  # Search operations
class WorkflowPort(Protocol):      # Session workflow
class DiagnosticsPort(Protocol):   # Stats and health

# Composite interface for backward compatibility
class DatabasePort(
    MemoryReadPort,
    MemoryWritePort,
    MemorySearchPort,
    WorkflowPort,
    DiagnosticsPort,
    Protocol
):
    """Use specific ports for new code, DatabasePort for existing code."""
    pass
```

### Dependency Injection

```python
from gmemory.container import get_container

# Get services via DI container
container = get_container()
db = container.get_database()       # DatabasePort
embedder = container.get_embedder() # EmbedderPort
config = container.get_config()     # ConfigPort

# Testing: inject mocks
container.set_database(mock_db)
container.set_embedder(mock_embedder)
```

### Error Handling

Structured error codes follow the pattern `GMEM-{CATEGORY}-{NUMBER}`:

| Category | Range | Description |
|----------|-------|-------------|
| CFG | 001-099 | Configuration errors |
| EMB | 100-199 | Embedding errors |
| DB | 200-299 | Database errors |
| SCN | 300-399 | Scanner errors |
| CMD | 400-499 | Command errors |

```python
from gmemory.errors import DatabaseError, ErrorCode

raise DatabaseError(
    code=ErrorCode.DB_MEMORY_NOT_FOUND,
    message="Memory not found",
    details={"memory_id": "mem_123"}
)
```

## Maintenance

### Health Check

```bash
gmemory health              # Standard check
gmemory health --verbose    # Detailed diagnostics
gmemory health --quick      # Quick status
```

### Rebuild Indexes

```bash
gmemory reindex --target=embeddings --apply  # After model change
gmemory reindex --target=fts --apply         # Rebuild FTS
gmemory reindex --target=tags --apply        # Rebuild tags
```

### Database Maintenance

```bash
gmemory compact                    # VACUUM + ANALYZE
gmemory purge --days=180 --apply   # Purge old memories
gmemory lifecycle-stats            # View statistics
```

## Comparison with Similar Tools

| Feature | GMemory | claude-mem | memex | opencode-mem |
|---------|---------|------------|-------|--------------|
| Language | Python | TypeScript | Rust | TypeScript |
| Storage | SQLite + sqlite-vec | SQLite + Chroma | Tantivy + usearch | SQLite + sqlite-vec |
| Search | Hybrid (vec+FTS) | Hybrid (vec+FTS) | BM25 + semantic | Vector |
| Embeddings | Local (FastEmbed) | Local/Remote | Local (multiple) | Local (Xenova) |
| Interface | CLI only | Hooks + Web UI | CLI + TUI | Plugin + Web UI |
| Background | None | Worker service | Optional daemon | Plugin hooks |

### Why GMemory?

- **No runtime dependencies** beyond Python + SQLite
- **No background processes** required
- **Works offline** without network calls
- **Easily scriptable** and composable with other tools

## Scope & Non-Goals

| In Scope | Out of Scope |
|----------|--------------|
| CLI tool for OpenCode | Web UI / Dashboard |
| Local SQLite storage | Cloud sync / Remote storage |
| Local embeddings (FastEmbed) | External embedding APIs |
| Manual distillation workflow | Automatic summarization |
| Single-user local use | Multi-user / Collaboration |
| Batch CLI operations | Background services / Daemons |

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Quick test
uv run pytest tests/ -q --tb=no

# Specific module
uv run pytest tests/test_search_modes.py -v
```

## License

MIT
