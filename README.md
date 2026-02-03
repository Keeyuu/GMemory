# GMemory

Local Agent Persistent Memory System.

## Overview

GMemory is a tool designed to provide persistent memory for AI Agents. It scans Agent session logs, allows for distillation of key information, and stores it in a local SQLite database with vector search capabilities.

## Features

- **Session Scanning**: Fetch unprocessed sessions from OpenCode.
- **Memory Distillation**: Refine session content into actionable technical points.
- **Vector Search**: Search through memories using semantic similarity (powered by `sqlite-vec` and Ollama).
- **CRUD Operations**: Manually add, update, or delete memories.

## Installation

```bash
pip install -e .
```

## Usage

```bash
python -m gmemory --help
```

### Commands

- `fetch`: Get unprocessed sessions.
- `save`: Save distilled memory and mark session.
- `search`: Semantic search through memories.
- `add`: Manually add memory.
- `stats`: Show system statistics.

## Configuration

Default configuration is stored in `config.toml`. You can override it by creating `~/.gmemory/config.toml`.
