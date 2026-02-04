"""Maintenance CLI commands for GMemory.

Rebuild, diagnostics, health, lifecycle, embedding profiles.
"""

import click
import json

from gmemory.config import config
from gmemory.commands.rebuild import rebuild_embeddings, rebuild_fts_index
from gmemory.commands.lifecycle import (
    purge_old_memories,
    compact_database,
    reindex_all,
    get_lifecycle_stats,
)
from gmemory.commands.embedding_profiles import (
    list_embedding_profiles,
    get_embedding_profile_detail,
    check_profile_compatibility,
    switch_embedding_profile,
    get_index_version_info,
)
from gmemory.commands.health import check_index_health, quick_health_check
from gmemory.commands.profiles import (
    get_profile,
    list_profiles,
    get_profile_names,
    format_profile_table,
    format_profile_detail,
)
from gmemory.commands.dedupe import find_duplicates, merge_memories, auto_dedupe


def register_maintenance_commands(cli: click.Group) -> None:
    """Register maintenance commands."""

    @cli.command("rebuild")
    @click.option(
        "--target",
        type=click.Choice(["embeddings", "fts", "all"]),
        default="all",
        help="What to rebuild.",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Show what would be done without making changes.",
    )
    @click.option(
        "--batch-size", default=50, help="Number of memories to process at a time."
    )
    def rebuild_cmd(target, dry_run, batch_size):
        """Rebuild embeddings and/or FTS index."""
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

    @cli.command("diagnostics")
    def diagnostics_cmd():
        """Show database diagnostics and health status."""
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

    @cli.command("health")
    @click.option("--verbose", "-v", is_flag=True, help="Include detailed diagnostics.")
    @click.option(
        "--quick", "-q", is_flag=True, help="Quick check (faster, less detail)."
    )
    def health_cmd(verbose, quick):
        """Check index health and identify issues."""
        try:
            if quick:
                result = quick_health_check()
            else:
                result = check_index_health(verbose=verbose)
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("purge")
    @click.option("--days", type=int, help="Delete memories older than N days.")
    @click.option(
        "--dry-run", is_flag=True, default=True, help="Preview what would be deleted."
    )
    @click.option("--apply", is_flag=True, help="Actually delete memories.")
    @click.option(
        "--archive/--no-archive", default=None, help="Archive memories before deletion."
    )
    @click.option("--archive-path", help="Custom path for archive file.")
    @click.option("--project", help="Only purge from specific project.")
    def purge_cmd(days, dry_run, apply, archive, archive_path, project):
        """Purge old memories based on retention policy."""
        try:
            effective_dry_run = not apply
            result = purge_old_memories(
                days=days,
                dry_run=effective_dry_run,
                archive=archive,
                archive_path=archive_path,
                project_path=project,
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("compact")
    @click.option(
        "--vacuum/--no-vacuum", default=True, help="Run VACUUM to reclaim space."
    )
    @click.option(
        "--analyze/--no-analyze",
        default=True,
        help="Run ANALYZE for query optimization.",
    )
    @click.option("--rebuild-fts", is_flag=True, help="Also rebuild FTS index.")
    def compact_cmd(vacuum, analyze, rebuild_fts):
        """Compact and optimize the database."""
        try:
            result = compact_database(
                vacuum=vacuum, analyze=analyze, rebuild_fts=rebuild_fts
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("reindex")
    @click.option(
        "--target",
        type=click.Choice(["all", "embeddings", "fts", "tags"]),
        default="all",
        help="What to reindex.",
    )
    @click.option(
        "--dry-run", is_flag=True, default=True, help="Preview what would be done."
    )
    @click.option("--apply", is_flag=True, help="Actually rebuild indexes.")
    def reindex_cmd(target, dry_run, apply):
        """Rebuild database indexes (embeddings, FTS, tags)."""
        try:
            effective_dry_run = not apply
            result = reindex_all(dry_run=effective_dry_run, target=target)
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("lifecycle-stats")
    def lifecycle_stats_cmd():
        """Show statistics for lifecycle management."""
        try:
            result = get_lifecycle_stats()
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("embedding-profiles")
    @click.argument("profile_name", required=False)
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
    def embedding_profiles_cmd(profile_name, as_json):
        """List embedding profiles or show details for one."""
        try:
            if profile_name:
                result = get_embedding_profile_detail(profile_name)
            else:
                result = list_embedding_profiles()

            if as_json or profile_name:
                click.echo(json.dumps(result, indent=2))
            else:
                profiles = result.get("profiles", [])
                active = result.get("active_profile", "")
                click.echo("Available Embedding Profiles:")
                click.echo("-" * 60)
                click.echo(f"{'Name':<15} {'Model':<20} {'Dim':<6} {'Status'}")
                click.echo("-" * 60)
                for p in profiles:
                    status = "* ACTIVE" if p["active"] else ""
                    click.echo(
                        f"{p['name']:<15} {p['model']:<20} {p['dimension']:<6} {status}"
                    )
                click.echo("-" * 60)
                click.echo(f"Active: {active}")
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("embedding-check")
    @click.argument("target_profile")
    def embedding_check_cmd(target_profile):
        """Check compatibility before switching embedding profile."""
        try:
            result = check_profile_compatibility(target_profile)
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("embedding-switch")
    @click.argument("target_profile")
    @click.option(
        "--rebuild", is_flag=True, help="Automatically rebuild indexes after switching."
    )
    @click.option(
        "--dry-run", is_flag=True, default=True, help="Preview what would happen."
    )
    @click.option("--apply", is_flag=True, help="Actually switch profile.")
    def embedding_switch_cmd(target_profile, rebuild, dry_run, apply):
        """Switch to a different embedding profile."""
        try:
            effective_dry_run = not apply
            result = switch_embedding_profile(
                target_profile=target_profile,
                rebuild=rebuild,
                dry_run=effective_dry_run,
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("index-info")
    def index_info_cmd():
        """Show index version and coverage information."""
        try:
            result = get_index_version_info()
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("profiles")
    @click.argument("profile_name", required=False)
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
    def profiles_cmd(profile_name, as_json):
        """List available search profiles or show details for one."""
        try:
            if profile_name:
                profile = get_profile(profile_name)
                if not profile:
                    click.echo(
                        json.dumps(
                            {
                                "error": f"Unknown profile: '{profile_name}'",
                                "available": get_profile_names(),
                            }
                        )
                    )
                    return
                if as_json:
                    click.echo(json.dumps(profile.to_dict(), indent=2))
                else:
                    click.echo(format_profile_detail(profile))
            else:
                if as_json:
                    profiles = [p.to_dict() for p in list_profiles()]
                    click.echo(json.dumps({"profiles": profiles}, indent=2))
                else:
                    click.echo(format_profile_table())
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("dedupe")
    @click.option(
        "--threshold", default=0.85, type=float, help="Similarity threshold (0.0-1.0)."
    )
    @click.option("--limit", default=50, help="Maximum memories to analyze.")
    @click.option("--project", help="Filter by project path.")
    @click.option("--min-group-size", default=2, help="Minimum group size to report.")
    @click.option(
        "--strategy",
        type=click.Choice(["vector", "simhash", "minhash"]),
        default="vector",
        help="Deduplication strategy.",
    )
    def dedupe_cmd(threshold, limit, project, min_group_size, strategy):
        """Find groups of similar/duplicate memories."""
        try:
            result = find_duplicates(
                threshold=threshold,
                limit=limit,
                project_path=project,
                min_group_size=min_group_size,
                strategy=strategy,
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("merge")
    @click.argument("memory_ids", nargs=-1, required=True)
    @click.option("--keep", help="ID of memory to keep.")
    @click.option(
        "--no-merge-tags", is_flag=True, help="Don't merge tags from all memories."
    )
    @click.option(
        "--dry-run", is_flag=True, help="Show what would happen without making changes."
    )
    def merge_cmd(memory_ids, keep, no_merge_tags, dry_run):
        """Merge multiple memories into one."""
        try:
            result = merge_memories(
                memory_ids=list(memory_ids),
                keep_id=keep,
                merge_tags=not no_merge_tags,
                dry_run=dry_run,
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("auto-dedupe")
    @click.option(
        "--threshold", default=0.95, type=float, help="Similarity threshold (0.0-1.0)."
    )
    @click.option("--limit", default=100, help="Maximum memories to analyze.")
    @click.option("--project", help="Filter by project path.")
    @click.option(
        "--dry-run",
        is_flag=True,
        default=True,
        help="Show what would happen without making changes.",
    )
    @click.option("--apply", is_flag=True, help="Actually apply the deduplication.")
    @click.option(
        "--strategy",
        type=click.Choice(["vector", "simhash", "minhash"]),
        default="vector",
        help="Deduplication strategy.",
    )
    def auto_dedupe_cmd(threshold, limit, project, dry_run, apply, strategy):
        """Automatically find and merge near-duplicate memories."""
        try:
            effective_dry_run = not apply
            result = auto_dedupe(
                threshold=threshold,
                limit=limit,
                project_path=project,
                dry_run=effective_dry_run,
                strategy=strategy,
            )
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))
