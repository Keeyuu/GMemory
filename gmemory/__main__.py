"""GMemory CLI entry point.

Uses modular CLI structure from gmemory.cli package.
"""

from gmemory.logging import configure_from_env
from gmemory.cli import cli, create_cli

# Configure logging from environment on import
configure_from_env()

# Create CLI with all command groups
create_cli()


def main():
    cli()


if __name__ == "__main__":
    main()
