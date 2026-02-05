"""Configuration CLI commands for GMemory.

Config templates, generation, initialization.
"""

import click

from gmemory.cli.error_handler import cli_command, output_json
from gmemory.config import (
    list_templates,
    get_template,
    generate_config_file,
    init_project_config,
    Config,
)
from gmemory.errors import ConfigError, ErrorCode


def register_config_commands(cli: click.Group) -> None:
    """Register configuration commands."""

    @cli.command("config-templates")
    @click.argument("template_name", required=False)
    @cli_command(indent=2)
    def config_templates_cmd(template_name):
        """List available configuration templates or show details for one."""
        if template_name:
            tpl = get_template(template_name)
            if not tpl:
                raise ConfigError(
                    code=ErrorCode.CONFIG_NOT_FOUND,
                    message=f"Unknown template: '{template_name}'",
                    details={"available": [t["name"] for t in list_templates()]},
                )
            return {"name": template_name, "config": tpl}
        else:
            return {"templates": list_templates()}

    @cli.command("config-generate")
    @click.option("--template", "-t", default="default", help="Template to use.")
    @click.option("--output", "-o", help="Output file path.")
    @click.option(
        "--project", "-p", help="Generate project-specific config in this directory."
    )
    @cli_command(indent=2)
    def config_generate_cmd(template, output, project):
        """Generate a configuration file from a template."""
        if project:
            result = init_project_config(
                project_path=project, template=template, force=False
            )
        elif output:
            result = generate_config_file(template=template, output_path=output)
        else:
            result = generate_config_file(template=template)

        if "content" in result and not output:
            # Output raw content for stdout, return None to skip JSON output
            click.echo(result["content"])
            return None
        return result

    @cli.command("config-init")
    @click.argument("project_path", default=".")
    @click.option("--template", "-t", default="default", help="Template to use.")
    @click.option("--force", "-f", is_flag=True, help="Overwrite existing config.")
    @cli_command(indent=2)
    def config_init_cmd(project_path, template, force):
        """Initialize project-specific configuration."""
        return init_project_config(
            project_path=project_path, template=template, force=force
        )

    @cli.command("config-show")
    @click.option("--project", "-p", help="Show config for specific project.")
    @cli_command(indent=2)
    def config_show_cmd(project):
        """Show current effective configuration."""
        if project:
            cfg = Config(project_path=project)
        else:
            cfg = Config()

        result = {
            "storage": {"db_path": str(cfg.db_path)},
            "embedding": {
                "provider": cfg.embedding_provider,
                "model": cfg.embedding_model,
                "dimension": cfg.embedding_dimension,
                "active_profile": cfg.embedding_active_profile,
            },
            "scanner": {"default_agent": cfg.default_agent},
            "search": {
                "default_mode": cfg.search_default_mode,
                "default_profile": cfg.search_default_profile,
                "default_limit": cfg.search_default_limit,
                "vector_weight": cfg.search_vector_weight,
                "fts_weight": cfg.search_fts_weight,
                "recency_weight": cfg.search_recency_weight,
                "min_score_threshold": cfg.search_min_score_threshold,
            },
            "lifecycle": {
                "retention_days": cfg.lifecycle_retention_days,
                "archive_before_purge": cfg.lifecycle_archive_before_purge,
            },
            "project": {
                "isolation_mode": cfg.project_isolation_mode,
                "auto_detect_root": cfg.project_auto_detect_root,
                "config_loaded": cfg.project_config_loaded,
            },
        }

        if project:
            result["project_path"] = project

        return result
