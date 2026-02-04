"""Structured logging configuration for GMemory."""

import logging
import sys
from pathlib import Path
from typing import Optional

# Log format with structured fields
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FORMAT_DEBUG = (
    "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d: %(message)s"
)

# Default log level
DEFAULT_LEVEL = logging.INFO


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    debug: bool = False,
) -> None:
    """Configure logging for GMemory.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path to write logs to.
        debug: If True, use debug format with function/line info.
    """
    # Determine log level
    if level:
        log_level = getattr(logging, level.upper(), DEFAULT_LEVEL)
    else:
        log_level = logging.DEBUG if debug else DEFAULT_LEVEL

    # Select format
    log_format = LOG_FORMAT_DEBUG if debug or log_level == logging.DEBUG else LOG_FORMAT

    # Configure root logger for gmemory
    root_logger = logging.getLogger("gmemory")
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (e.g., "gmemory.storage.database").

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


# Convenience function for CLI
def configure_from_env() -> None:
    """Configure logging from environment variables.

    Environment variables:
        GMEMORY_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        GMEMORY_LOG_FILE: Path to log file
        GMEMORY_DEBUG: Set to "1" or "true" for debug mode
    """
    import os

    level = os.environ.get("GMEMORY_LOG_LEVEL")
    log_file_str = os.environ.get("GMEMORY_LOG_FILE")
    debug = os.environ.get("GMEMORY_DEBUG", "").lower() in ("1", "true")

    log_file = Path(log_file_str) if log_file_str else None
    setup_logging(level=level, log_file=log_file, debug=debug)
