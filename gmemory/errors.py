"""Structured error types for GMemory.

Error codes follow the pattern: GMEM-{CATEGORY}-{NUMBER}
Categories:
- CFG: Configuration errors (001-099)
- EMB: Embedding errors (100-199)
- DB:  Database errors (200-299)
- SCN: Scanner errors (300-399)
- CMD: Command errors (400-499)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    """Enumeration of all GMemory error codes."""

    # Configuration errors (001-099)
    CONFIG_NOT_FOUND = "GMEM-CFG-001"
    CONFIG_INVALID = "GMEM-CFG-002"
    CONFIG_MISSING_KEY = "GMEM-CFG-003"

    # Embedding errors (100-199)
    EMBEDDING_PROVIDER_UNAVAILABLE = "GMEM-EMB-100"
    EMBEDDING_MODEL_NOT_FOUND = "GMEM-EMB-101"
    EMBEDDING_DIMENSION_MISMATCH = "GMEM-EMB-102"
    EMBEDDING_FAILED = "GMEM-EMB-103"
    EMBEDDING_INVALID = "GMEM-EMB-104"

    # Database errors (200-299)
    DB_CONNECTION_FAILED = "GMEM-DB-200"
    DB_SCHEMA_ERROR = "GMEM-DB-201"
    DB_QUERY_FAILED = "GMEM-DB-202"
    DB_MEMORY_NOT_FOUND = "GMEM-DB-203"
    DB_VECTOR_DIMENSION_MISMATCH = "GMEM-DB-204"
    DB_FTS_ERROR = "GMEM-DB-205"

    # Scanner errors (300-399)
    SCANNER_NOT_FOUND = "GMEM-SCN-300"
    SCANNER_PATH_NOT_FOUND = "GMEM-SCN-301"
    SCANNER_PARSE_ERROR = "GMEM-SCN-302"
    SCANNER_SESSION_INVALID = "GMEM-SCN-303"

    # Command errors (400-499)
    CMD_INVALID_ARGUMENT = "GMEM-CMD-400"
    CMD_MISSING_REQUIRED = "GMEM-CMD-401"
    CMD_OPERATION_FAILED = "GMEM-CMD-402"
    CMD_SEARCH_FAILED = "GMEM-CMD-403"


@dataclass
class GMemoryError(Exception):
    """Base exception for GMemory with structured error information."""

    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        result = {
            "error": True,
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


# Convenience subclasses for specific error categories


class ConfigError(GMemoryError):
    """Configuration-related errors."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.CONFIG_INVALID,
        message: str = "Configuration error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=code, message=message, details=details)


class EmbeddingError(GMemoryError):
    """Embedding-related errors."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.EMBEDDING_FAILED,
        message: str = "Embedding error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=code, message=message, details=details)


class DatabaseError(GMemoryError):
    """Database-related errors."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.DB_QUERY_FAILED,
        message: str = "Database error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=code, message=message, details=details)


class ScannerError(GMemoryError):
    """Scanner-related errors."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.SCANNER_PARSE_ERROR,
        message: str = "Scanner error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=code, message=message, details=details)


class CommandError(GMemoryError):
    """Command-related errors."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.CMD_OPERATION_FAILED,
        message: str = "Command error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=code, message=message, details=details)


def format_error_response(error: Exception) -> Dict[str, Any]:
    """Format any exception as a structured error response.

    Args:
        error: Exception to format.

    Returns:
        Dictionary suitable for JSON serialization.
    """
    if isinstance(error, GMemoryError):
        return error.to_dict()

    # Generic error fallback
    return {
        "error": True,
        "code": "GMEM-ERR-999",
        "message": str(error),
    }
