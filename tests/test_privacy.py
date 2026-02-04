"""Tests for privacy utilities."""

import pytest
from gmemory.utils.privacy import (
    strip_private_tags,
    has_private_content,
    extract_private_content,
)


class TestStripPrivateTags:
    """Tests for strip_private_tags function."""

    def test_no_private_tags(self):
        """Text without private tags should be unchanged."""
        text = "Hello world, this is normal text."
        cleaned, count = strip_private_tags(text)
        assert cleaned == text
        assert count == 0

    def test_single_private_tag(self):
        """Single private tag should be stripped."""
        text = "Hello <private>secret</private> world"
        cleaned, count = strip_private_tags(text)
        assert cleaned == "Hello world"
        assert count == 1

    def test_multiple_private_tags(self):
        """Multiple private tags should all be stripped."""
        text = "Start <private>secret1</private> middle <private>secret2</private> end"
        cleaned, count = strip_private_tags(text)
        assert cleaned == "Start middle end"
        assert count == 2

    def test_multiline_private_content(self):
        """Private tags spanning multiple lines should be stripped."""
        text = """Before
<private>
This is
multiline
secret
</private>
After"""
        cleaned, count = strip_private_tags(text)
        assert "Before" in cleaned
        assert "After" in cleaned
        assert "secret" not in cleaned
        assert count == 1

    def test_case_insensitive(self):
        """Private tags should be case-insensitive."""
        text = "Hello <PRIVATE>secret</PRIVATE> world"
        cleaned, count = strip_private_tags(text)
        assert cleaned == "Hello world"
        assert count == 1

    def test_mixed_case(self):
        """Mixed case private tags should work."""
        text = "Hello <Private>secret</pRiVaTe> world"
        cleaned, count = strip_private_tags(text)
        assert cleaned == "Hello world"
        assert count == 1

    def test_self_closing_tag(self):
        """Self-closing private tags should be stripped."""
        text = "Hello <private/> world"
        cleaned, count = strip_private_tags(text)
        assert cleaned == "Hello world"
        assert count == 1

    def test_empty_string(self):
        """Empty string should return empty."""
        cleaned, count = strip_private_tags("")
        assert cleaned == ""
        assert count == 0

    def test_none_input(self):
        """None input should return None."""
        cleaned, count = strip_private_tags(None)
        assert cleaned is None
        assert count == 0

    def test_nested_content_preserved(self):
        """Content outside private tags should be fully preserved."""
        text = "API key: <private>sk-12345</private>, User: john"
        cleaned, count = strip_private_tags(text)
        assert "API key:" in cleaned
        assert "User: john" in cleaned
        assert "sk-12345" not in cleaned

    def test_unicode_content(self):
        """Unicode content should be preserved."""
        text = "你好 <private>秘密</private> 世界"
        cleaned, count = strip_private_tags(text)
        assert "你好" in cleaned
        assert "世界" in cleaned
        assert "秘密" not in cleaned
        assert count == 1


class TestHasPrivateContent:
    """Tests for has_private_content function."""

    def test_no_private_content(self):
        """Text without private tags returns False."""
        assert has_private_content("Hello world") is False

    def test_has_private_content(self):
        """Text with private tags returns True."""
        assert has_private_content("Hello <private>secret</private>") is True

    def test_self_closing_tag(self):
        """Self-closing tag returns True."""
        assert has_private_content("Hello <private/>") is True

    def test_empty_string(self):
        """Empty string returns False."""
        assert has_private_content("") is False


class TestExtractPrivateContent:
    """Tests for extract_private_content function."""

    def test_extract_single(self):
        """Extract single private content."""
        text = "Hello <private>secret</private> world"
        content = extract_private_content(text)
        assert content == ["secret"]

    def test_extract_multiple(self):
        """Extract multiple private contents."""
        text = "A <private>one</private> B <private>two</private> C"
        content = extract_private_content(text)
        assert content == ["one", "two"]

    def test_extract_none(self):
        """No private content returns empty list."""
        content = extract_private_content("Hello world")
        assert content == []

    def test_extract_empty(self):
        """Empty string returns empty list."""
        content = extract_private_content("")
        assert content == []
