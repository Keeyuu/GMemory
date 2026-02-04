import click
import json
import sys
from gmemory.logging import configure_from_env
from gmemory.config import config
from gmemory.commands.fetch import fetch_unprocessed_sessions
from gmemory.commands.save import save_memory
from gmemory.commands.mark import mark_session
from gmemory.commands.search import search_memories
from gmemory.commands.get import get_memories
from gmemory.commands.list import list_memories
from gmemory.commands.add import add_memory
from gmemory.commands.update import update_memory
from gmemory.commands.delete import delete_memory
from gmemory.commands.stats import get_stats
from gmemory.commands.rebuild import rebuild_embeddings, rebuild_fts_index
from gmemory.commands.workflow import process_sessions, save_batch, skip_session

# Configure logging from environment on import
configure_from_env()


@click.group()
def cli():
    """GMemory: Local Agent Persistent Memory System."""
    pass


@cli.command()
@click.option("--limit", default=5, help="Limit the number of sessions to fetch.")
@click.option("--agent", default="opencode", help="Agent type to fetch sessions for.")
def fetch(limit, agent):
    """Fetch unprocessed sessions from Agent logs."""
    try:
        result = fetch_unprocessed_sessions(limit=limit, agent=agent)
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command()
@click.option(
    "--session-id", required=True, help="Session ID to associate with the memory."
)
@click.option("--content", required=True, help="Distilled memory content.")
@click.option("--tags", help="Comma-separated tags.")
@click.option(
    "--importance", default="medium", help="Importance level (high/medium/low)."
)
@click.option("--type", help="Memory type.")
def save(session_id, content, tags, importance, type):
    """Save a distilled memory and mark session as processed."""
    try:
        # Use default from save_memory if type is None
        kwargs = {}
        if type:
            kwargs["memory_type"] = type

        result = save_memory(
            session_id=session_id,
            content=content,
            tags=tags,
            importance=importance,
            **kwargs,
        )
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command()
@click.option("--session-id", required=True, help="Session ID to mark as processed.")
def mark(session_id):
    """Mark a session as processed without saving a memory."""
    try:
        result = mark_session(session_id=session_id)
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command()
@click.argument("query")
@click.option("--project", help="Filter by project path.")
@click.option("--tags", help="Filter by tags (comma-separated).")
@click.option("--limit", default=5, help="Limit the number of results.")
@click.option(
    "--compact", is_flag=True, help="Return compact results (id, tags, preview only)."
)
@click.option(
    "--mode",
    default="hybrid",
    type=click.Choice(["hybrid", "vector", "fts"]),
    help="Search mode: hybrid (vector+FTS), vector-only, or fts-only.",
)
@click.option(
    "--recency",
    default=0.0,
    type=float,
    help="Recency weight (0.0-1.0). Higher values favor recent memories.",
)
@click.option(
    "--include-superseded",
    is_flag=True,
    help="Include memories that have been superseded by newer ones.",
)
def search(query, project, tags, limit, compact, mode, recency, include_superseded):
    """Search memories using vector similarity."""
    try:
        result = search_memories(
            query=query,
            project_path=project,
            tags=tags,
            limit=limit,
            compact=compact,
            mode=mode,
            recency_weight=recency,
            include_superseded=include_superseded,
        )
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command()
@click.option("--content", required=True, help="Memory content.")
@click.option("--tags", help="Comma-separated tags.")
@click.option("--importance", default="medium", help="Importance level.")
def add(content, tags, importance):
    """Add a new memory manually."""
    try:
        result = add_memory(content=content, tags=tags, importance=importance)
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command()
@click.argument("mem_id")
@click.option("--content", help="New memory content.")
@click.option("--tags", help="New tags.")
def update(mem_id, content, tags):
    """Update an existing memory."""
    try:
        result = update_memory(mem_id=mem_id, content=content, tags=tags)
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command()
@click.argument("mem_id")
def delete(mem_id):
    """Delete a memory."""
    try:
        result = delete_memory(mem_id=mem_id)
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command("get")
@click.argument("ids", nargs=-1, required=True)
@click.option("--no-metadata", is_flag=True, help="Exclude metadata from results.")
def get_cmd(ids, no_metadata):
    """Get full memory content by ID(s).

    Usage: gmemory get <id1> [id2] [id3] ...

    This is the second layer of progressive disclosure:
    1. search --compact → get IDs and previews
    2. get <ids> → get full content
    """
    try:
        result = get_memories(list(ids), include_metadata=not no_metadata)
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command()
def stats():
    """Show memory system statistics."""
    try:
        result = get_stats()
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command("list")
@click.option("--limit", default=20, help="Maximum number of results.")
@click.option("--offset", default=0, help="Number of results to skip (pagination).")
@click.option("--project", help="Filter by project path.")
@click.option("--importance", help="Filter by importance (high/medium/low).")
@click.option(
    "--sort", default="updated_at", help="Sort by field (created_at, updated_at)."
)
@click.option("--order", default="desc", help="Sort order (asc, desc).")
def list_cmd(limit, offset, project, importance, sort, order):
    """List memories without search query.

    Browse all memories with optional filtering and pagination.
    This is the lightweight overview layer - no embedding required.

    Progressive disclosure:
    1. list → browse all memories
    2. search --compact → semantic search with previews
    3. get <ids> → full content
    """
    try:
        result = list_memories(
            limit=limit,
            offset=offset,
            project_path=project,
            importance=importance,
            sort_by=sort,
            sort_order=order,
        )
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command("rebuild")
@click.option(
    "--target",
    type=click.Choice(["embeddings", "fts", "all"]),
    default="all",
    help="What to rebuild: embeddings, fts index, or all.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without making changes.",
)
@click.option(
    "--batch-size",
    default=50,
    help="Number of memories to process at a time (for embeddings).",
)
def rebuild_cmd(target, dry_run, batch_size):
    """Rebuild embeddings and/or FTS index.

    Use this when:
    - Switching embedding models
    - Embedding dimension changes
    - Index becomes corrupted
    - Upgrading from NoOp to real embeddings

    Examples:
        gmemory rebuild --target=embeddings --dry-run
        gmemory rebuild --target=fts
        gmemory rebuild --target=all
    """
    try:
        results = {}

        if target in ("embeddings", "all"):
            results["embeddings"] = rebuild_embeddings(
                dry_run=dry_run, batch_size=batch_size
            )

        if target in ("fts", "all"):
            if not dry_run:
                results["fts"] = rebuild_fts_index()
            else:
                results["fts"] = {
                    "dry_run": True,
                    "message": "Would rebuild FTS index.",
                }

        click.echo(json.dumps(results))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command("process")
@click.option("--limit", default=5, help="Maximum sessions to fetch.")
@click.option("--agent", default="opencode", help="Agent type.")
def process_cmd(limit, agent):
    """Fetch unprocessed sessions for review (workflow step 1).

    This is the lightweight workflow entry point:
    1. gmemory process → get sessions to review
    2. Review and distill content
    3. gmemory save --session-id=X --content=Y (for each)
       or gmemory mark --session-id=X (to skip)

    Example workflow:
        gmemory process --limit=3
        # Review output, then for each session:
        gmemory save --session-id=abc123 --content="Key insight..." --tags="python,api"
    """
    try:
        result = process_sessions(limit=limit, agent=agent)
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command("diagnostics")
def diagnostics_cmd():
    """Show database diagnostics and health status.

    Displays information about:
    - sqlite-vec extension status
    - Vector dimension configuration
    - Schema version and pending migrations
    - Memory/index counts
    """
    try:
        from gmemory.storage.database import MemoryDatabase

        db = MemoryDatabase()
        try:
            diag = db.get_diagnostics()
            latest_run = db.get_latest_scan_run(
                scanner=config.default_agent, agent=config.default_agent
            )
            if latest_run:
                diag["latest_scan_run"] = latest_run

            actions = []
            if not diag.get("vec_extension_loaded", True):
                actions.append(
                    {
                        "issue": "sqlite-vec extension not loaded",
                        "action": "Install sqlite-vec",
                        "command": "pip install sqlite-vec",
                    }
                )

            if diag.get("vec_dimension_mismatch"):
                actions.append(
                    {
                        "issue": "Vector dimension mismatch",
                        "action": "Rebuild embeddings",
                        "command": "gmemory rebuild --target=embeddings",
                    }
                )

            if diag.get("fts_count", 0) < diag.get("memory_count", 0):
                actions.append(
                    {
                        "issue": "FTS index out of sync",
                        "action": "Rebuild FTS index",
                        "command": "gmemory rebuild --target=fts",
                    }
                )

            if diag.get("scan_errors", 0) > 0:
                actions.append(
                    {
                        "issue": "Unresolved scan errors",
                        "action": "Review and resolve scan errors",
                        "command": "gmemory scan-errors --limit=50",
                    }
                )
                diag["scan_errors_preview"] = db.get_scan_errors(limit=5)

            if actions:
                diag["actions"] = actions

            click.echo(json.dumps(diag, indent=2))
        finally:
            db.close()
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command("scan-runs")
@click.option("--limit", default=20, help="Maximum number of scan runs.")
def scan_runs_cmd(limit: int):
    """List recent scan runs for observability."""
    try:
        from gmemory.storage.database import MemoryDatabase

        db = MemoryDatabase()
        try:
            runs = db.get_scan_runs(limit=limit)
            click.echo(json.dumps({"runs": runs, "total": len(runs)}, indent=2))
        finally:
            db.close()
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command("scan-errors")
@click.option("--limit", default=50, help="Maximum number of errors to show.")
@click.option(
    "--all", "include_resolved", is_flag=True, help="Include resolved errors."
)
def scan_errors_cmd(limit: int, include_resolved: bool):
    """List scan errors for manual recovery."""
    try:
        from gmemory.storage.database import MemoryDatabase

        db = MemoryDatabase()
        try:
            errors = db.get_scan_errors(
                limit=limit, unresolved_only=not include_resolved
            )
            click.echo(
                json.dumps(
                    {
                        "errors": errors,
                        "total": len(errors),
                        "unresolved_only": not include_resolved,
                    },
                    indent=2,
                )
            )
        finally:
            db.close()
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


@cli.command("scan-errors-resolve")
@click.argument("ids", nargs=-1, required=True)
@click.option("--note", help="Resolution note.")
def scan_errors_resolve_cmd(ids: tuple, note=None):
    """Resolve scan errors after manual review."""
    try:
        from gmemory.storage.database import MemoryDatabase

        parsed_ids = []
        invalid_ids = []
        for raw_id in ids:
            try:
                parsed_ids.append(int(raw_id))
            except ValueError:
                invalid_ids.append(raw_id)

        if invalid_ids:
            click.echo(
                json.dumps(
                    {
                        "error": "Invalid scan error id(s)",
                        "invalid_ids": invalid_ids,
                    }
                )
            )
            return

        db = MemoryDatabase()
        try:
            result = db.resolve_scan_errors(parsed_ids, note=note)
            click.echo(json.dumps(result, indent=2))
        finally:
            db.close()
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


def main():
    cli()


if __name__ == "__main__":
    main()
