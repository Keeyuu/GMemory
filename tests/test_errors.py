"""Tests for error types."""

import pytest
from gmemory.errors import (
    ErrorCode,
    GMemoryError,
    ConfigError,
    EmbeddingError,
    DatabaseError,
    ScannerError,
    CommandError,
    format_error_response,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_code_format(self):
        """Error codes should follow GMEM-XXX-NNN format."""
        for code in ErrorCode:
            assert code.value.startswith("GMEM-")
            parts = code.value.split("-")
            assert len(parts) == 3
            assert parts[0] == "GMEM"
            assert len(parts[1]) <= 3  # Category
            assert parts[2].isdigit()  # Number


class TestGMemoryError:
    """Tests for GMemoryError base class."""

    def test_error_str(self):
        """Error string should include code and message."""
        error = GMemoryError(
            code=ErrorCode.EMBEDDING_FAILED,
            message="Test error message",
        )
        error_str = str(error)
        assert "GMEM-EMB-103" in error_str
        assert "Test error message" in error_str

    def test_error_to_dict(self):
        """Error should serialize to dict correctly."""
        error = GMemoryError(
            code=ErrorCode.DB_MEMORY_NOT_FOUND,
            message="Memory not found",
            details={"memory_id": "test-123"},
        )
        result = error.to_dict()
        assert result["error"] is True
        assert result["code"] == "GMEM-DB-203"
        assert result["message"] == "Memory not found"
        assert result["details"]["memory_id"] == "test-123"

    def test_error_without_details(self):
        """Error without details should not include details key."""
        error = GMemoryError(
            code=ErrorCode.CONFIG_NOT_FOUND,
            message="Config not found",
        )
        result = error.to_dict()
        assert "details" not in result


class TestErrorSubclasses:
    """Tests for error subclasses."""

    def test_config_error(self):
        """ConfigError should have correct defaults."""
        error = ConfigError(message="Invalid config")
        assert error.code == ErrorCode.CONFIG_INVALID
        assert "Invalid config" in str(error)

    def test_embedding_error(self):
        """EmbeddingError should have correct defaults."""
        error = EmbeddingError(message="Model not found")
        assert error.code == ErrorCode.EMBEDDING_FAILED
        assert "Model not found" in str(error)

    def test_database_error(self):
        """DatabaseError should have correct defaults."""
        error = DatabaseError(message="Query failed")
        assert error.code == ErrorCode.DB_QUERY_FAILED
        assert "Query failed" in str(error)

    def test_scanner_error(self):
        """ScannerError should have correct defaults."""
        error = ScannerError(message="Parse error")
        assert error.code == ErrorCode.SCANNER_PARSE_ERROR
        assert "Parse error" in str(error)

    def test_command_error(self):
        """CommandError should have correct defaults."""
        error = CommandError(message="Operation failed")
        assert error.code == ErrorCode.CMD_OPERATION_FAILED
        assert "Operation failed" in str(error)


class TestFormatErrorResponse:
    """Tests for format_error_response function."""

    def test_format_gmemory_error(self):
        """GMemoryError should format correctly."""
        error = EmbeddingError(
            code=ErrorCode.EMBEDDING_DIMENSION_MISMATCH,
            message="Dimension mismatch",
        )
        result = format_error_response(error)
        assert result["error"] is True
        assert result["code"] == "GMEM-EMB-102"

    def test_format_generic_exception(self):
        """Generic exceptions should format with fallback code."""
        error = ValueError("Something went wrong")
        result = format_error_response(error)
        assert result["error"] is True
        assert result["code"] == "GMEM-ERR-999"
        assert "Something went wrong" in result["message"]
