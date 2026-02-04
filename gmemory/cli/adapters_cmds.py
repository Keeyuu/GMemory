"""Source adapter CLI commands for GMemory.

List sources, detect source type.
"""

import click
import json
from pathlib import Path

from gmemory.scanner.adapters import list_sources, get_source_info, detect_source


def register_adapter_commands(cli: click.Group) -> None:
    """Register source adapter commands."""

    @cli.command("sources")
    @click.argument("source_name", required=False)
    def sources_cmd(source_name):
        """List available source adapters or show details for one."""
        try:
            if source_name:
                result = get_source_info(source_name)
            else:
                result = list_sources()
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))

    @cli.command("detect-source")
    @click.argument("path")
    def detect_source_cmd(path):
        """Detect the source type from a directory."""
        try:
            detected = detect_source(Path(path).expanduser())
            if detected:
                result = {
                    "path": path,
                    "detected_source": detected,
                    "adapter_info": get_source_info(detected),
                }
            else:
                result = {
                    "path": path,
                    "detected_source": None,
                    "message": "Could not detect source type",
                }
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}))
