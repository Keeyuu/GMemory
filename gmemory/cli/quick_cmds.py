"""Quick access CLI commands for GMemory.

Shortcut commands for common operations: q, recent, today, tag, tags.
"""

import click

from gmemory.cli.error_handler import cli_command
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
    @cli_command(indent=2)
    def quick_search_cmd(query, limit, days):
        """Quick search shortcut (alias for search --compact)."""
        return quick_search(query=query, limit=limit, recent_days=days)

    @cli.command("recent")
    @click.option("--days", "-d", default=7, help="Look back N days.")
    @click.option("--limit", "-n", default=10, help="Maximum results.")
    @click.option("--project", "-p", help="Filter by project path.")
    @click.option("--tags", "-t", help="Filter by tags (comma-separated).")
    @cli_command(indent=2)
    def recent_cmd(days, limit, project, tags):
        """Show most recent memories."""
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        return recent_memories(
            days=days, limit=limit, project_path=project, tags=tag_list
        )

    @cli.command("today")
    @cli_command(indent=2)
    def today_cmd():
        """Show today's activity summary."""
        return today_summary()

    @cli.command("tag")
    @click.argument("tag_name")
    @click.option("--limit", "-n", default=20, help="Maximum results.")
    @click.option("--full", is_flag=True, help="Show full content.")
    @cli_command(indent=2)
    def tag_cmd(tag_name, limit, full):
        """Find memories by tag."""
        return find_by_tag(tag=tag_name, limit=limit, compact=not full)

    @cli.command("tags")
    @click.option("--limit", "-n", default=50, help="Maximum tags to show.")
    @cli_command(indent=2)
    def tags_cmd(limit):
        """List all tags with counts."""
        return list_all_tags(limit=limit)
