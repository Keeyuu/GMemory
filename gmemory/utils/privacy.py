"""Privacy tag utilities for GMemory.

Implements <private>...</private> tag stripping to exclude sensitive content
from memory storage, following claude-mem's privacy control pattern.
"""

import re
from typing import Optional, Tuple

# Pattern to match <private>...</private> tags (case-insensitive, multiline)
PRIVATE_TAG_PATTERN = re.compile(
    r"<private\s*>.*?</private\s*>",
    re.IGNORECASE | re.DOTALL,
)

# Pattern to match self-closing <private/> tags
PRIVATE_SELF_CLOSING_PATTERN = re.compile(
    r"<private\s*/\s*>",
    re.IGNORECASE,
)


def strip_private_tags(text: Optional[str]) -> Tuple[Optional[str], int]:
    """Remove <private>...</private> tagged content from text.

    Args:
        text: Input text that may contain private tags.

    Returns:
        Tuple of (cleaned_text, count_of_stripped_sections).

    Example:
        >>> strip_private_tags("Hello <private>secret</private> world")
        ('Hello  world', 1)
    """
    if not text:
        return text, 0

    # Count matches before stripping
    matches = PRIVATE_TAG_PATTERN.findall(text)
    count = len(matches)

    # Strip private content
    cleaned = PRIVATE_TAG_PATTERN.sub("", text)

    # Also handle self-closing tags
    self_closing_matches = PRIVATE_SELF_CLOSING_PATTERN.findall(cleaned)
    count += len(self_closing_matches)
    cleaned = PRIVATE_SELF_CLOSING_PATTERN.sub("", cleaned)

    # Clean up multiple spaces left by removal
    cleaned = re.sub(r"  +", " ", cleaned)

    return cleaned.strip(), count


def has_private_content(text: str) -> bool:
    """Check if text contains any private tags.

    Args:
        text: Input text to check.

    Returns:
        True if private tags are present.
    """
    if not text:
        return False

    return bool(
        PRIVATE_TAG_PATTERN.search(text) or PRIVATE_SELF_CLOSING_PATTERN.search(text)
    )


def extract_private_content(text: str) -> list[str]:
    """Extract all private-tagged content from text.

    Useful for debugging or auditing what would be stripped.

    Args:
        text: Input text containing private tags.

    Returns:
        List of content strings that were inside private tags.
    """
    if not text:
        return []

    # Extract content between tags
    content_pattern = re.compile(
        r"<private\s*>(.*?)</private\s*>",
        re.IGNORECASE | re.DOTALL,
    )

    return content_pattern.findall(text)
