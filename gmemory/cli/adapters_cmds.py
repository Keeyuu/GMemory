"""Source adapter CLI commands for GMemory.

List sources, detect source type.
"""

import click
from pathlib import Path

from gmemory.cli.error_handler import cli_command
from gmemory.scanner.adapters import list_sources, get_source_info, detect_source


def register_adapter_commands(cli: click.Group) -> None:
    """Register source adapter commands."""

    @cli.command("sources")
    @click.argument("source_name", required=False)
    @cli_command(indent=2)
    def sources_cmd(source_name):
        """List available source adapters or show details for one."""
        if source_name:
            return get_source_info(source_name)
        else:
            return list_sources()

    @cli.command("detect-source")
    @click.argument("path")
    @cli_command(indent=2)
    def detect_source_cmd(path):
        """Detect the source type from a directory."""
        detected = detect_source(Path(path).expanduser())
        if detected:
            return {
                "path": path,
                "detected_source": detected,
                "adapter_info": get_source_info(detected),
            }
        else:
            return {
                "path": path,
                "detected_source": None,
                "message": "Could not detect source type",
            }
