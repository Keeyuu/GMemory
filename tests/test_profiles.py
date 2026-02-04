"""Tests for search profiles."""

import pytest
from gmemory.commands.profiles import (
    SearchProfile,
    BUILTIN_PROFILES,
    get_profile,
    list_profiles,
    get_profile_names,
    format_profile_table,
    format_profile_detail,
    DEFAULT_PROFILE,
)


class TestSearchProfile:
    """Tests for SearchProfile dataclass."""

    def test_profile_creation(self):
        """Test creating a search profile."""
        profile = SearchProfile(
            name="test",
            description="Test profile",
            mode="hybrid",
            recency_weight=0.5,
        )
        assert profile.name == "test"
        assert profile.description == "Test profile"
        assert profile.mode == "hybrid"
        assert profile.recency_weight == 0.5

    def test_profile_to_dict(self):
        """Test profile serialization to dict."""
        profile = SearchProfile(
            name="test",
            description="Test",
            mode="vector",
            recency_weight=0.3,
            use_tag_index=True,
            tag_weight=0.5,
        )
        d = profile.to_dict()
        assert d["name"] == "test"
        assert d["mode"] == "vector"
        assert d["recency_weight"] == 0.3
        assert d["use_tag_index"] is True
        assert d["tag_weight"] == 0.5

    def test_get_search_params(self):
        """Test extracting search parameters from profile."""
        profile = SearchProfile(
            name="test",
            description="Test",
            mode="fts",
            recency_weight=0.7,
            use_tag_index=True,
            tag_weight=0.4,
        )
        params = profile.get_search_params()
        assert params["mode"] == "fts"
        assert params["recency_weight"] == 0.7
        assert params["use_tag_index"] is True
        assert params["tag_weight"] == 0.4


class TestBuiltinProfiles:
    """Tests for built-in profiles."""

    def test_all_profiles_have_required_fields(self):
        """Test that all profiles have required fields."""
        for name, profile in BUILTIN_PROFILES.items():
            assert profile.name == name
            assert profile.description
            assert profile.mode in ("hybrid", "vector", "fts")
            assert 0.0 <= profile.recency_weight <= 1.0
            assert 0.0 <= profile.tag_weight <= 1.0
            assert isinstance(profile.use_tag_index, bool)

    def test_balanced_profile(self):
        """Test balanced profile configuration."""
        profile = BUILTIN_PROFILES["balanced"]
        assert profile.mode == "hybrid"
        assert profile.recency_weight == 0.0
        assert profile.use_tag_index is False

    def test_semantic_profile(self):
        """Test semantic profile configuration."""
        profile = BUILTIN_PROFILES["semantic"]
        assert profile.mode == "vector"
        assert profile.vector_weight == 1.0
        assert profile.fts_weight == 0.0

    def test_keyword_profile(self):
        """Test keyword profile configuration."""
        profile = BUILTIN_PROFILES["keyword"]
        assert profile.mode == "fts"

    def test_recent_profile(self):
        """Test recent profile configuration."""
        profile = BUILTIN_PROFILES["recent"]
        assert profile.recency_weight > 0
        assert profile.recency_weight < 1.0

    def test_very_recent_profile(self):
        """Test very-recent profile configuration."""
        profile = BUILTIN_PROFILES["very-recent"]
        assert profile.recency_weight >= 0.7

    def test_tag_heavy_profile(self):
        """Test tag-heavy profile configuration."""
        profile = BUILTIN_PROFILES["tag-heavy"]
        assert profile.use_tag_index is True
        assert profile.tag_weight >= 0.5

    def test_tag_only_profile(self):
        """Test tag-only profile configuration."""
        profile = BUILTIN_PROFILES["tag-only"]
        assert profile.use_tag_index is True
        assert profile.tag_weight >= 0.7

    def test_fresh_tags_profile(self):
        """Test fresh-tags profile configuration."""
        profile = BUILTIN_PROFILES["fresh-tags"]
        assert profile.use_tag_index is True
        assert profile.recency_weight > 0


class TestProfileFunctions:
    """Tests for profile utility functions."""

    def test_get_profile_existing(self):
        """Test getting an existing profile."""
        profile = get_profile("balanced")
        assert profile is not None
        assert profile.name == "balanced"

    def test_get_profile_case_insensitive(self):
        """Test profile lookup is case-insensitive."""
        profile = get_profile("BALANCED")
        assert profile is not None
        assert profile.name == "balanced"

    def test_get_profile_nonexistent(self):
        """Test getting a non-existent profile returns None."""
        profile = get_profile("nonexistent")
        assert profile is None

    def test_list_profiles_returns_all(self):
        """Test listing all profiles."""
        profiles = list_profiles()
        assert len(profiles) == len(BUILTIN_PROFILES)
        for profile in profiles:
            assert profile.name in BUILTIN_PROFILES

    def test_list_profiles_sorted(self):
        """Test profiles are sorted by name."""
        profiles = list_profiles()
        names = [p.name for p in profiles]
        assert names == sorted(names)

    def test_get_profile_names(self):
        """Test getting profile names."""
        names = get_profile_names()
        assert "balanced" in names
        assert "semantic" in names
        assert "keyword" in names
        assert names == sorted(names)

    def test_default_profile_exists(self):
        """Test default profile exists."""
        profile = get_profile(DEFAULT_PROFILE)
        assert profile is not None


class TestProfileFormatting:
    """Tests for profile formatting functions."""

    def test_format_profile_table(self):
        """Test table formatting includes all profiles."""
        table = format_profile_table()
        assert "balanced" in table
        assert "semantic" in table
        assert "keyword" in table
        assert "Mode" in table
        assert "Recency" in table

    def test_format_profile_detail(self):
        """Test detail formatting includes all fields."""
        profile = BUILTIN_PROFILES["balanced"]
        detail = format_profile_detail(profile)
        assert "balanced" in detail
        assert "mode:" in detail
        assert "recency_weight:" in detail
        assert "use_tag_index:" in detail
        assert "tag_weight:" in detail
