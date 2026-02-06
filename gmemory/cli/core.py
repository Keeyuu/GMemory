"""Core CLI commands for GMemory.

Basic CRUD operations: fetch, save, mark, search, get, list, add, update, delete, stats.
"""

import click

from gmemory.cli.error_handler import handle_cli_error
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
from gmemory.commands.profiles import get_profile_names


def register_core_commands(cli: click.Group) -> None:
    """Register core CRUD commands."""

    @cli.command()
    @click.option("--limit", default=5, help="Limit the number of sessions to fetch.")
    @click.option(
        "--agent", default="opencode", help="Agent type to fetch sessions for."
    )
    @handle_cli_error
    def fetch(limit, agent):
        """Fetch unprocessed sessions from Agent logs."""
        return fetch_unprocessed_sessions(limit=limit, agent=agent)

    @cli.command()
    @click.option(
        "--session-id", required=True, help="Session ID to associate with the memory."
    )
    @click.option("--content", required=True, help="Distilled memory content.")
    @click.option("--tags", help="Comma-separated tags.")
    @click.option(
        "--importance", default="medium", help="Importance level (high/medium/low)."
    )
    @click.option("--type", "memory_type", help="Memory type.")
    @handle_cli_error
    def save(session_id, content, tags, importance, memory_type):
        """Save a distilled memory and mark session as processed."""
        kwargs = {}
        if memory_type:
            kwargs["memory_type"] = memory_type
        return save_memory(
            session_id=session_id,
            content=content,
            tags=tags,
            importance=importance,
            **kwargs,
        )

    @cli.command()
    @click.option(
        "--session-id", required=True, help="Session ID to mark as processed."
    )
    @click.option("--status", default="processed", help="Processing status.")
    @click.option("--reason", help="Reason for marking.")
    @handle_cli_error
    def mark(session_id, status, reason):
        """Mark a session as processed without saving a memory."""
        return mark_session(session_id=session_id, status=status, reason=reason)

    @cli.command()
    @click.argument("query")
    @click.option("--project", help="Filter by project path.")
    @click.option("--tags", help="Filter by tags (comma-separated).")
    @click.option("--limit", default=5, help="Limit the number of results.")
    @click.option(
        "--compact",
        is_flag=True,
        help="Return compact results (id, tags, preview only).",
    )
    @click.option(
        "--mode", type=click.Choice(["hybrid", "vector", "fts"]), help="Search mode."
    )
    @click.option("--recency", type=float, help="Recency weight (0.0-1.0).")
    @click.option(
        "--include-superseded", is_flag=True, help="Include superseded memories."
    )
    @click.option("--explain", is_flag=True, help="Include detailed scoring breakdown.")
    @click.option("--use-tag-index", is_flag=True, help="Use dual vector index.")
    @click.option(
        "--tag-weight", type=float, help="Weight for tag similarity (0.0-1.0)."
    )
    @click.option(
        "--profile",
        "-p",
        type=click.Choice(get_profile_names()),
        help="Search profile preset.",
    )
    @click.option("--min-score", type=float, help="Minimum score threshold (0.0-1.0).")
    @handle_cli_error
    def search(
        query,
        project,
        tags,
        limit,
        compact,
        mode,
        recency,
        include_superseded,
        explain,
        use_tag_index,
        tag_weight,
        profile,
        min_score,
    ):
        """Search memories using vector similarity."""
        return search_memories(
            query=query,
            project_path=project,
            tags=tags,
            limit=limit,
            compact=compact,
            mode=mode,
            recency_weight=recency,
            include_superseded=include_superseded,
            explain=explain,
            use_tag_index=use_tag_index,
            tag_weight=tag_weight,
            profile=profile,
            min_score=min_score,
        )

    @cli.command("get")
    @click.argument("ids", nargs=-1, required=True)
    @click.option("--no-metadata", is_flag=True, help="Exclude metadata from results.")
    @handle_cli_error
    def get_cmd(ids, no_metadata):
        """Get full memory content by ID(s)."""
        return get_memories(list(ids), include_metadata=not no_metadata)

    @cli.command("list")
    @click.option("--limit", default=20, help="Maximum number of results.")
    @click.option("--offset", default=0, help="Number of results to skip.")
    @click.option("--project", help="Filter by project path.")
    @click.option("--importance", help="Filter by importance (high/medium/low).")
    @click.option("--sort", default="updated_at", help="Sort by field.")
    @click.option("--order", default="desc", help="Sort order (asc, desc).")
    @handle_cli_error
    def list_cmd(limit, offset, project, importance, sort, order):
        """List memories without search query."""
        return list_memories(
            limit=limit,
            offset=offset,
            project_path=project,
            importance=importance,
            sort_by=sort,
            sort_order=order,
        )

    @cli.command()
    @click.option("--content", required=True, help="Memory content.")
    @click.option("--preview", required=True, help="Agent-provided preview text.")
    @click.option("--tags", help="Comma-separated tags.")
    @click.option("--importance", default="medium", help="Importance level.")
    @handle_cli_error
    def add(content, preview, tags, importance):
        """Add a new memory manually."""
        return add_memory(
            content=content,
            preview=preview,
            tags=tags,
            importance=importance,
        )

    @cli.command()
    @click.argument("mem_id")
    @click.option("--content", required=True, help="New memory content.")
    @click.option("--preview", required=True, help="New agent-provided preview text.")
    @click.option("--tags", help="New tags.")
    @handle_cli_error
    def update(mem_id, content, preview, tags):
        """Update an existing memory."""
        return update_memory(
            mem_id=mem_id,
            content=content,
            preview=preview,
            tags=tags,
        )

    @cli.command()
    @click.argument("mem_id")
    @handle_cli_error
    def delete(mem_id):
        """Delete a memory."""
        return delete_memory(mem_id=mem_id)

    @cli.command()
    @handle_cli_error
    def stats():
        """Show memory system statistics."""
        return get_stats()
