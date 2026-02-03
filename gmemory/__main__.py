import click
import json
import sys
from gmemory.commands.fetch import fetch_unprocessed_sessions
from gmemory.commands.save import save_memory
from gmemory.commands.mark import mark_session
from gmemory.commands.search import search_memories
from gmemory.commands.add import add_memory
from gmemory.commands.update import update_memory
from gmemory.commands.delete import delete_memory
from gmemory.commands.stats import get_stats


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
def search(query, project, tags, limit):
    """Search memories using vector similarity."""
    try:
        result = search_memories(
            query=query, project_path=project, tags=tags, limit=limit
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


@cli.command()
def stats():
    """Show memory system statistics."""
    try:
        result = get_stats()
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


def main():
    cli()


if __name__ == "__main__":
    main()
