# Issues

## [2026-02-03] Verification Blockers

- LSP unavailable on Windows + Bun v1.3.5 (Segmentation fault warning).
- Python executable (`python`/`py`) missing in bash environment, preventing CLI verification.

## [2026-02-03] LSP Configuration

- `lsp_diagnostics` failed: no LSP server configured for empty extension at project root.

## [2026-02-03] Integration Testing Blocked

- Python not available in shell environment (Windows Store alias present but not a real Python install).
- Cannot run `python -m gmemory` or `pip install -e .` to verify CLI functionality.
- All Python code is written and reviewed but runtime verification requires Python installation.

**Recommendation for User**: 
1. Install Python 3.10+ from python.org
2. Run `pip install -e .` in project root
3. Run verification commands:
   - `python -m gmemory --help`
   - `python -m gmemory stats`
   - `python -m gmemory add --content "test" --tags "test"`
   - `python -m gmemory search "test"`

## [2026-02-03] Ollama Service Required

- Ollama server not running (port 11434 not reachable).
- Commands requiring embeddings (add, save, search) will fail with 502 error.
- Commands NOT requiring embeddings work: stats, fetch, mark, delete.

**Recommendation**:
1. Start Ollama: `ollama serve`
2. Pull embedding model: `ollama pull nomic-embed-text`
3. Then run embedding-dependent commands
