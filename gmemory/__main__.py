import click
import json
import sys


@click.group()
def cli():
    """GMemory: Local Agent Persistent Memory System."""
    pass


@cli.command()
@click.option("--limit", default=5, help="Limit the number of sessions to fetch.")
@click.option("--agent", default="opencode", help="Agent type to fetch sessions for.")
def fetch(limit, agent):
    """Fetch unprocessed sessions from Agent logs."""
    click.echo(json.dumps({"sessions": [], "has_more": False, "remaining": 0}))


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
    click.echo(
        json.dumps({"memory_id": "stub", "created": True, "session_marked": True})
    )


@cli.command()
@click.option("--session-id", required=True, help="Session ID to mark as processed.")
def mark(session_id):
    """Mark a session as processed without saving a memory."""
    click.echo(json.dumps({"session_id": session_id, "marked": True}))


@cli.command()
@click.argument("query")
@click.option("--project", help="Filter by project path.")
@click.option("--tags", help="Filter by tags (comma-separated).")
@click.option("--limit", default=5, help="Limit the number of results.")
def search(query, project, tags, limit):
    """Search memories using vector similarity."""
    click.echo(json.dumps({"results": [], "total": 0}))


@cli.command()
@click.option("--content", required=True, help="Memory content.")
@click.option("--tags", help="Comma-separated tags.")
@click.option("--importance", default="medium", help="Importance level.")
def add(content, tags, importance):
    """Add a new memory manually."""
    click.echo(json.dumps({"id": "stub", "created": True}))


@cli.command()
@click.argument("mem_id")
@click.option("--content", help="New memory content.")
@click.option("--tags", help="New tags.")
def update(mem_id, content, tags):
    """Update an existing memory."""
    click.echo(json.dumps({"id": mem_id, "updated": True}))


@cli.command()
@click.argument("mem_id")
def delete(mem_id):
    """Delete a memory."""
    click.echo(json.dumps({"id": mem_id, "deleted": True}))


@cli.command()
def stats():
    """Show memory system statistics."""
    click.echo(
        json.dumps(
            {
                "total_memories": 0,
                "unprocessed_sessions": 0,
                "by_project": {},
                "by_importance": {},
            }
        )
    )


def main():
    cli()


if __name__ == "__main__":
    main()
