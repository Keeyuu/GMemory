"""GMemory CLI module.

Organizes CLI commands into logical groups for maintainability.
"""

import click

from gmemory.cli.core import register_core_commands
from gmemory.cli.workflow import register_workflow_commands
from gmemory.cli.maintenance import register_maintenance_commands
from gmemory.cli.export_cmds import register_export_commands
from gmemory.cli.config_cmds import register_config_commands
from gmemory.cli.quick_cmds import register_quick_commands
from gmemory.cli.adapters_cmds import register_adapter_commands


@click.group()
def cli():
    """GMemory: Local Agent Persistent Memory System."""
    pass


def create_cli() -> click.Group:
    """Create and configure the CLI with all command groups."""
    register_core_commands(cli)
    register_workflow_commands(cli)
    register_maintenance_commands(cli)
    register_export_commands(cli)
    register_config_commands(cli)
    register_quick_commands(cli)
    register_adapter_commands(cli)
    return cli
