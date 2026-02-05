"""Tests for CLI output format."""

import json
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from gmemory.cli import cli
from gmemory.cli.error_handler import (
    handle_cli_error,
    cli_command,
    format_cli_output,
    output_json,
    output_error,
)
from gmemory.errors import GMemoryError, ErrorCode, CommandError


class TestErrorHandler:
    """Tests for error handler decorators."""

    def test_handle_cli_error_success(self):
        """Should output JSON for successful return."""

        @handle_cli_error
        def success_cmd():
            return {"status": "ok"}

        result = success_cmd()
        assert result == {"status": "ok"}

    def test_format_cli_output_compact(self):
        """Should format output as compact JSON by default."""
        data = {"key": "value", "nested": {"a": 1}}
        output = format_cli_output(data)

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed == data
        # Should be compact (no newlines)
        assert "\n" not in output

    def test_format_cli_output_indented(self):
        """Should format output with indentation when specified."""
        data = {"key": "value"}
        output = format_cli_output(data, indent=2)

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed == data
        # Should have newlines (indented)
        assert "\n" in output

    def test_format_cli_output_unicode(self):
        """Should preserve Unicode characters."""
        data = {"message": "你好世界", "emoji": "🎉"}
        output = format_cli_output(data)

        assert "你好世界" in output
        assert "🎉" in output


class TestCLICommands:
    """Tests for CLI command output format."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_profiles_list_function(self):
        """Profiles list function should return valid data."""
        from gmemory.commands.profiles import list_profiles

        profiles = list_profiles()

        assert isinstance(profiles, list)
        assert len(profiles) > 0
        # Each profile should have required fields
        for p in profiles:
            assert hasattr(p, "name")
            assert hasattr(p, "description")
            assert hasattr(p, "mode")


class TestErrorOutput:
    """Tests for error output format."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_gmemory_error_has_code(self):
        """GMemoryError should include error code in output."""
        error = CommandError(
            code=ErrorCode.CMD_INVALID_ARGUMENT,
            message="Invalid argument provided",
            details={"argument": "limit", "value": -1},
        )

        error_dict = error.to_dict()

        assert "code" in error_dict
        assert "GMEM-CMD-400" in error_dict["code"]
        assert "message" in error_dict
        assert "details" in error_dict

    def test_output_error_gmemory_error(self, capsys):
        """output_error should format GMemoryError correctly."""
        error = CommandError(
            code=ErrorCode.CMD_OPERATION_FAILED, message="Operation failed"
        )

        output_error(error)

        captured = capsys.readouterr()
        output = json.loads(captured.err)
        assert "code" in output
        assert "message" in output

    def test_output_error_generic_exception(self, capsys):
        """output_error should format generic exceptions."""
        error = ValueError("Something went wrong")

        output_error(error)

        captured = capsys.readouterr()
        output = json.loads(captured.err)
        assert "error" in output or "message" in output


class TestOutputJson:
    """Tests for output_json utility."""

    def test_output_json_dict(self, capsys):
        """Should output dict as JSON."""
        output_json({"key": "value"})

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"key": "value"}

    def test_output_json_list(self, capsys):
        """Should output list as JSON."""
        output_json([1, 2, 3])

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == [1, 2, 3]

    def test_output_json_with_indent(self, capsys):
        """Should respect indent parameter."""
        output_json({"key": "value"}, indent=2)

        captured = capsys.readouterr()
        assert "\n" in captured.out  # Indented output has newlines


class TestCliCommandDecorator:
    """Tests for @cli_command decorator behavior."""

    def test_cli_command_returns_result(self):
        """@cli_command should return function result."""

        @cli_command(indent=2)
        def test_func():
            return {"status": "ok"}

        # The decorator wraps the function but still returns the result
        result = test_func()
        assert result == {"status": "ok"}

    def test_cli_command_handles_none_return(self, capsys):
        """@cli_command should handle None return gracefully."""

        @cli_command(indent=2)
        def test_func():
            return None

        result = test_func()
        assert result is None

        # Should not output anything for None
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_cli_command_catches_gmemory_error(self):
        """@cli_command should catch and format GMemoryError."""

        @cli_command(indent=2)
        def test_func():
            raise CommandError(
                code=ErrorCode.CMD_OPERATION_FAILED, message="Test error"
            )

        with pytest.raises(SystemExit) as exc_info:
            test_func()

        assert exc_info.value.code == 1

    def test_cli_command_catches_generic_error(self):
        """@cli_command should catch and format generic exceptions."""

        @cli_command(indent=2)
        def test_func():
            raise ValueError("Generic error")

        with pytest.raises(SystemExit) as exc_info:
            test_func()

        assert exc_info.value.code == 1
