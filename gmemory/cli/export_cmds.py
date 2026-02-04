"""Export CLI commands for GMemory.

Session export, report export, memory export.
"""

import click
import json

from gmemory.commands.export import export_session, export_report, export_memories


def register_export_commands(cli: click.Group) -> None:
    """Register export commands."""

    @cli.command("session-export")
    @click.argument("session_id")
    @click.option(
        "--format",
        "fmt",
        type=click.Choice(["markdown", "json"]),
        default="markdown",
        help="Output format.",
    )
    @click.option("--output", "-o", help="Output file path.")
    @click.option("--no-content", is_flag=True, help="Exclude full memory content.")
    def session_export_cmd(session_id, fmt, output, no_content):
        """Export a session's memories to Markdown or JSON."""
        try:
            result = export_session(
                session_id=session_id,
                format=fmt,
                include_content=not no_content,
                output_path=output,
            )
            if output and "content" not in result:
                click.echo(
                    json.dumps({k: v for k, v in result.items() if k != "content"})
                )
            elif "content" in result:
                click.echo(result["content"])
            else:
                click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("report-export")
    @click.option(
        "--format",
        "fmt",
        type=click.Choice(["markdown", "json"]),
        default="markdown",
        help="Output format.",
    )
    @click.option("--limit", default=20, help="Maximum sessions to include.")
    @click.option("--project", help="Filter by project path.")
    @click.option("--since", type=int, help="Only sessions from last N days.")
    @click.option("--output", "-o", help="Output file path.")
    def report_export_cmd(fmt, limit, project, since, output):
        """Export session aggregation report to Markdown or JSON."""
        try:
            result = export_report(
                format=fmt,
                limit=limit,
                project_path=project,
                since_days=since,
                output_path=output,
            )
            if output and "content" not in result:
                click.echo(
                    json.dumps({k: v for k, v in result.items() if k != "content"})
                )
            elif "content" in result:
                click.echo(result["content"])
            else:
                click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("export")
    @click.argument("memory_ids", nargs=-1)
    @click.option(
        "--format",
        "fmt",
        type=click.Choice(["markdown", "json"]),
        default="markdown",
        help="Output format.",
    )
    @click.option("--project", help="Filter by project path (if no IDs given).")
    @click.option("--tags", help="Filter by tags (comma-separated, if no IDs given).")
    @click.option("--limit", default=100, help="Maximum memories (if no IDs given).")
    @click.option("--output", "-o", help="Output file path.")
    def export_cmd(memory_ids, fmt, project, tags, limit, output):
        """Export memories to Markdown or JSON."""
        try:
            tag_list = None
            if tags:
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]

            result = export_memories(
                memory_ids=list(memory_ids) if memory_ids else None,
                project_path=project,
                tags=tag_list,
                limit=limit,
                format=fmt,
                output_path=output,
            )
            if output and "content" not in result:
                click.echo(
                    json.dumps({k: v for k, v in result.items() if k != "content"})
                )
            elif "content" in result:
                click.echo(result["content"])
            else:
                click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))
