"""Quick access CLI commands for GMemory.

Shortcut commands for common operations: q, recent, today, tag, tags.
"""

import click
import json

from gmemory.commands.quick import (
    quick_search,
    recent_memories,
    today_summary,
    find_by_tag,
    list_all_tags,
)


def register_quick_commands(cli: click.Group) -> None:
    """Register quick access commands."""

    @cli.command("q")
    @click.argument("query")
    @click.option("--limit", "-n", default=5, help="Number of results.")
    @click.option("--days", "-d", type=int, help="Boost memories from last N days.")
    def quick_search_cmd(query, limit, days):
        """Quick search shortcut (alias for search --compact)."""
        try:
            result = quick_search(query=query, limit=limit, recent_days=days)
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("recent")
    @click.option("--days", "-d", default=7, help="Look back N days.")
    @click.option("--limit", "-n", default=10, help="Maximum results.")
    @click.option("--project", "-p", help="Filter by project path.")
    @click.option("--tags", "-t", help="Filter by tags (comma-separated).")
    def recent_cmd(days, limit, project, tags):
        """Show most recent memories."""
        try:
            tag_list = None
            if tags:
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            result = recent_memories(
                days=days, limit=limit, project_path=project, tags=tag_list
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("today")
    def today_cmd():
        """Show today's activity summary."""
        try:
            result = today_summary()
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("tag")
    @click.argument("tag_name")
    @click.option("--limit", "-n", default=20, help="Maximum results.")
    @click.option("--full", is_flag=True, help="Show full content.")
    def tag_cmd(tag_name, limit, full):
        """Find memories by tag."""
        try:
            result = find_by_tag(tag=tag_name, limit=limit, compact=not full)
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("tags")
    @click.option("--limit", "-n", default=50, help="Maximum tags to show.")
    def tags_cmd(limit):
        """List all tags with counts."""
        try:
            result = list_all_tags(limit=limit)
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))
