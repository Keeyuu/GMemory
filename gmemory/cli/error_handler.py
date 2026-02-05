"""Unified error handling for GMemory CLI.

Provides decorators and utilities for consistent error output across all CLI commands.
"""

import functools
import json
import sys
from typing import Any, Callable, TypeVar, Optional

import click

from gmemory.errors import GMemoryError, format_error_response

F = TypeVar("F", bound=Callable[..., Any])


def format_cli_output(data: Any, indent: Optional[int] = None) -> str:
    """Format data for CLI output as JSON.

    Args:
        data: Data to format.
        indent: JSON indentation level. None for compact output.

    Returns:
        JSON string.
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)


def handle_cli_error(func: F) -> F:
    """Decorator for unified CLI error handling.

    Wraps a CLI command function to:
    1. Catch GMemoryError and output structured error with code
    2. Catch unexpected exceptions and format them consistently
    3. Set appropriate exit codes

    Usage:
        @cli.command()
        @handle_cli_error
        def my_command():
            return {"result": "success"}
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            result = func(*args, **kwargs)
            if result is not None:
                click.echo(format_cli_output(result))
            return result
        except GMemoryError as e:
            # Preserve structured error info with code
            click.echo(format_cli_output(e.to_dict()), err=True)
            sys.exit(1)
        except click.exceptions.Exit:
            # Let Click handle its own exit
            raise
        except click.exceptions.Abort:
            # Let Click handle abort
            raise
        except Exception as e:
            # Fallback for unexpected errors - still structured
            error_response = format_error_response(e)
            click.echo(format_cli_output(error_response), err=True)
            sys.exit(1)

    return wrapper  # type: ignore[return-value]


def cli_command(indent: Optional[int] = None) -> Callable[[F], F]:
    """Decorator factory for CLI commands with configurable output.

    Args:
        indent: JSON indentation for output. None for compact, 2 for pretty.

    Usage:
        @cli.command()
        @cli_command(indent=2)
        def my_command():
            return {"result": "success"}
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    click.echo(format_cli_output(result, indent=indent))
                return result
            except GMemoryError as e:
                click.echo(format_cli_output(e.to_dict(), indent=indent), err=True)
                sys.exit(1)
            except click.exceptions.Exit:
                raise
            except click.exceptions.Abort:
                raise
            except Exception as e:
                error_response = format_error_response(e)
                click.echo(format_cli_output(error_response, indent=indent), err=True)
                sys.exit(1)

        return wrapper  # type: ignore[return-value]

    return decorator


def output_json(data: Any, indent: Optional[int] = None) -> None:
    """Output data as JSON to stdout.

    Convenience function for commands that need to output multiple times
    or have complex output logic.

    Args:
        data: Data to output.
        indent: JSON indentation level.
    """
    click.echo(format_cli_output(data, indent=indent))


def output_error(error: Exception, indent: Optional[int] = None) -> None:
    """Output error as JSON to stderr.

    Args:
        error: Exception to output.
        indent: JSON indentation level.
    """
    if isinstance(error, GMemoryError):
        click.echo(format_cli_output(error.to_dict(), indent=indent), err=True)
    else:
        click.echo(
            format_cli_output(format_error_response(error), indent=indent), err=True
        )
