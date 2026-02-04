"""Data validation for GMemory.

Provides validation functions for Memory and other data models to ensure
data quality at write time.
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple

from gmemory.errors import ErrorCode, GMemoryError


class ValidationError(GMemoryError):
    """Validation-related errors."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.CMD_INVALID_ARGUMENT,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=code, message=message, details=details)


# Valid importance levels
VALID_IMPORTANCE_LEVELS = {"high", "medium", "low"}

# Valid memory types (extensible)
VALID_MEMORY_TYPES = {
    "insight",
    "decision",
    "pattern",
    "bug",
    "solution",
    "architecture",
    "preference",
    "workflow",
    "learning",
    "context",
    None,  # Allow None for untyped memories
}

# Memory ID pattern: alphanumeric with optional hyphens/underscores
MEMORY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Maximum content length (to prevent accidental huge entries)
MAX_CONTENT_LENGTH = 100_000  # 100KB

# Maximum tag length and count
MAX_TAG_LENGTH = 100
MAX_TAGS_COUNT = 50


def validate_memory_id(memory_id: str) -> Tuple[bool, Optional[str]]:
    """Validate memory ID format.

    Args:
        memory_id: The memory ID to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not memory_id:
        return False, "Memory ID cannot be empty"

    if len(memory_id) > 255:
        return False, f"Memory ID too long: {len(memory_id)} > 255 chars"

    if not MEMORY_ID_PATTERN.match(memory_id):
        return False, "Memory ID must be alphanumeric with optional hyphens/underscores"

    return True, None


def validate_content(content: str) -> Tuple[bool, Optional[str]]:
    """Validate memory content.

    Args:
        content: The content to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not content:
        return False, "Content cannot be empty"

    if not content.strip():
        return False, "Content cannot be whitespace only"

    if len(content) > MAX_CONTENT_LENGTH:
        return False, f"Content too long: {len(content)} > {MAX_CONTENT_LENGTH} chars"

    return True, None


def validate_tags(tags: List[str]) -> Tuple[bool, Optional[str]]:
    """Validate tags list.

    Args:
        tags: List of tags to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if len(tags) > MAX_TAGS_COUNT:
        return False, f"Too many tags: {len(tags)} > {MAX_TAGS_COUNT}"

    for tag in tags:
        if not tag or not tag.strip():
            return False, "Tags cannot be empty or whitespace"

        if len(tag) > MAX_TAG_LENGTH:
            return False, f"Tag too long: '{tag[:20]}...' > {MAX_TAG_LENGTH} chars"

        # Tags should be lowercase alphanumeric with hyphens
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", tag.lower()):
            # Allow but warn - don't fail on this
            pass

    return True, None


def validate_importance(importance: str) -> Tuple[bool, Optional[str]]:
    """Validate importance level.

    Args:
        importance: The importance level to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if importance not in VALID_IMPORTANCE_LEVELS:
        return (
            False,
            f"Invalid importance '{importance}'. Must be one of: {VALID_IMPORTANCE_LEVELS}",
        )

    return True, None


def validate_memory_type(memory_type: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate memory type.

    Args:
        memory_type: The memory type to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if memory_type is not None and memory_type not in VALID_MEMORY_TYPES:
        # Allow unknown types but log warning - extensibility
        pass

    return True, None


def validate_timestamp(
    timestamp: int, field_name: str = "timestamp"
) -> Tuple[bool, Optional[str]]:
    """Validate Unix timestamp.

    Args:
        timestamp: The timestamp to validate.
        field_name: Name of the field for error messages.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if timestamp < 0:
        return False, f"{field_name} cannot be negative"

    # Sanity check: not before 2020 and not more than 1 year in future
    min_ts = 1577836800  # 2020-01-01
    max_ts = int(time.time()) + 365 * 24 * 3600

    if timestamp < min_ts:
        return False, f"{field_name} too old: before 2020"

    if timestamp > max_ts:
        return False, f"{field_name} too far in future"

    return True, None


def validate_memory(
    memory_id: str,
    content: str,
    tags: List[str],
    importance: str = "medium",
    memory_type: Optional[str] = None,
    created_at: Optional[int] = None,
    updated_at: Optional[int] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """Validate all memory fields.

    Args:
        memory_id: Memory ID.
        content: Memory content.
        tags: List of tags.
        importance: Importance level.
        memory_type: Memory type.
        created_at: Creation timestamp.
        updated_at: Update timestamp.
        strict: If True, raise ValidationError on failure.

    Returns:
        Dict with 'valid' bool and 'errors' list.

    Raises:
        ValidationError: If strict=True and validation fails.
    """
    errors = []

    # Validate each field
    valid, err = validate_memory_id(memory_id)
    if not valid:
        errors.append(f"id: {err}")

    valid, err = validate_content(content)
    if not valid:
        errors.append(f"content: {err}")

    valid, err = validate_tags(tags)
    if not valid:
        errors.append(f"tags: {err}")

    valid, err = validate_importance(importance)
    if not valid:
        errors.append(f"importance: {err}")

    valid, err = validate_memory_type(memory_type)
    if not valid:
        errors.append(f"memory_type: {err}")

    if created_at is not None:
        valid, err = validate_timestamp(created_at, "created_at")
        if not valid:
            errors.append(err)

    if updated_at is not None:
        valid, err = validate_timestamp(updated_at, "updated_at")
        if not valid:
            errors.append(err)

    result = {"valid": len(errors) == 0, "errors": errors}

    if strict and errors:
        raise ValidationError(
            code=ErrorCode.CMD_INVALID_ARGUMENT,
            message="Memory validation failed",
            details={"errors": errors},
        )

    return result
