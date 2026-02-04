"""Workflow CLI commands for GMemory.

Process, batch operations, scan error management.
"""

import click
import json

from gmemory.commands.workflow import (
    process_sessions,
    mark_all_sessions,
    get_scan_error_summary,
    batch_resolve_errors,
)
from gmemory.commands.session_report import get_session_report, get_session_detail


def register_workflow_commands(cli: click.Group) -> None:
    """Register workflow commands."""

    @cli.command("process")
    @click.option("--limit", default=5, help="Maximum sessions to fetch.")
    @click.option("--agent", default="opencode", help="Agent type.")
    def process_cmd(limit, agent):
        """Fetch unprocessed sessions for review (workflow step 1)."""
        try:
            result = process_sessions(limit=limit, agent=agent)
            click.echo(json.dumps(result))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("mark-all")
    @click.option("--agent", default="opencode", help="Agent type.")
    @click.option("--limit", default=10, help="Maximum sessions to mark.")
    @click.option(
        "--dry-run", is_flag=True, default=True, help="Preview what would be marked."
    )
    @click.option("--apply", is_flag=True, help="Actually mark sessions.")
    def mark_all_cmd(agent, limit, dry_run, apply):
        """Mark multiple unprocessed sessions as processed (batch skip)."""
        try:
            effective_dry_run = not apply
            result = mark_all_sessions(
                agent=agent, limit=limit, dry_run=effective_dry_run
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("backlog")
    @click.option("--agent", default="opencode", help="Agent type.")
    def backlog_cmd(agent):
        """Show backlog status and workflow suggestions."""
        try:
            result = process_sessions(limit=10, agent=agent, show_backlog=True)
            summary = {
                "status": result.get("status", "unknown"),
                "pending_sessions": result.get("total", 0),
                "backlog": result.get("backlog", {}),
                "workflow": result.get("workflow", {}),
                "hint": result.get("hint", ""),
            }
            click.echo(json.dumps(summary, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("scan-runs")
    @click.option("--limit", default=20, help="Maximum number of scan runs.")
    def scan_runs_cmd(limit):
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
    def scan_errors_cmd(limit, include_resolved):
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
    def scan_errors_resolve_cmd(ids, note):
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

    @cli.command("scan-errors-summary")
    def scan_errors_summary_cmd():
        """Get a summary of scan errors with suggested actions."""
        try:
            result = get_scan_error_summary()
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("scan-errors-batch-resolve")
    @click.argument("ids", nargs=-1)
    @click.option(
        "--all", "resolve_all", is_flag=True, help="Resolve all unresolved errors."
    )
    @click.option("--note", help="Resolution note.")
    @click.option(
        "--dry-run", is_flag=True, default=True, help="Preview what would be resolved."
    )
    @click.option("--apply", is_flag=True, help="Actually resolve errors.")
    def scan_errors_batch_resolve_cmd(ids, resolve_all, note, dry_run, apply):
        """Batch resolve scan errors."""
        try:
            effective_dry_run = not apply
            parsed_ids = None
            if ids:
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

            if not parsed_ids and not resolve_all:
                click.echo(
                    json.dumps({"error": "Must specify error IDs or use --all flag"})
                )
                return

            result = batch_resolve_errors(
                error_ids=parsed_ids,
                resolve_all=resolve_all,
                note=note,
                dry_run=effective_dry_run,
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("session-report")
    @click.option("--limit", default=20, help="Maximum number of sessions to show.")
    @click.option("--project", help="Filter by project path.")
    @click.option("--since", type=int, help="Only sessions from last N days.")
    @click.option(
        "--include-empty", is_flag=True, help="Include sessions with no memories."
    )
    def session_report_cmd(limit, project, since, include_empty):
        """Generate session-level aggregation report."""
        try:
            result = get_session_report(
                limit=limit,
                project_path=project,
                include_empty=include_empty,
                since_days=since,
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("session-detail")
    @click.argument("session_id")
    @click.option("--full", is_flag=True, help="Include full memory content.")
    def session_detail_cmd(session_id, full):
        """Get detailed information about a specific session."""
        try:
            result = get_session_detail(session_id, include_content=full)
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))
