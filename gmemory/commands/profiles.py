"""Search profiles for GMemory.

Profiles provide pre-configured search parameter sets for common use cases.
Each profile defines weights for vector, FTS, recency, and tag scoring.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Optional, List


@dataclass(frozen=True)
class SearchProfile:
    """A search profile with predefined scoring weights.

    Attributes:
        name: Profile identifier.
        description: Human-readable description of the profile's purpose.
        mode: Search mode (hybrid, vector, fts).
        recency_weight: Weight for recency boost (0.0-1.0).
        use_tag_index: Whether to use dual vector index.
        tag_weight: Weight for tag similarity (0.0-1.0).
        vector_weight: Weight for vector similarity in hybrid mode.
        fts_weight: Weight for FTS in hybrid mode.
    """

    name: str
    description: str
    mode: str = "hybrid"
    recency_weight: float = 0.0
    use_tag_index: bool = False
    tag_weight: float = 0.3
    vector_weight: float = 0.7
    fts_weight: float = 0.3

    def to_dict(self) -> Dict:
        """Convert profile to dictionary."""
        return asdict(self)

    def get_search_params(self) -> Dict:
        """Get parameters suitable for search_memories() call."""
        return {
            "mode": self.mode,
            "recency_weight": self.recency_weight,
            "use_tag_index": self.use_tag_index,
            "tag_weight": self.tag_weight,
        }


# Built-in search profiles
BUILTIN_PROFILES: Dict[str, SearchProfile] = {
    "balanced": SearchProfile(
        name="balanced",
        description="Default balanced search using vector + FTS hybrid scoring",
        mode="hybrid",
        recency_weight=0.0,
        use_tag_index=False,
        tag_weight=0.3,
        vector_weight=0.7,
        fts_weight=0.3,
    ),
    "semantic": SearchProfile(
        name="semantic",
        description="Pure semantic search using vector similarity only",
        mode="vector",
        recency_weight=0.0,
        use_tag_index=False,
        tag_weight=0.0,
        vector_weight=1.0,
        fts_weight=0.0,
    ),
    "keyword": SearchProfile(
        name="keyword",
        description="Full-text keyword search using FTS5 only",
        mode="fts",
        recency_weight=0.0,
        use_tag_index=False,
        tag_weight=0.0,
        vector_weight=0.0,
        fts_weight=1.0,
    ),
    "recent": SearchProfile(
        name="recent",
        description="Favor recent memories with moderate recency boost",
        mode="hybrid",
        recency_weight=0.4,
        use_tag_index=False,
        tag_weight=0.3,
        vector_weight=0.7,
        fts_weight=0.3,
    ),
    "very-recent": SearchProfile(
        name="very-recent",
        description="Strongly favor recent memories (last few days)",
        mode="hybrid",
        recency_weight=0.7,
        use_tag_index=False,
        tag_weight=0.3,
        vector_weight=0.7,
        fts_weight=0.3,
    ),
    "tag-heavy": SearchProfile(
        name="tag-heavy",
        description="Prioritize tag similarity using dual vector index",
        mode="hybrid",
        recency_weight=0.0,
        use_tag_index=True,
        tag_weight=0.6,
        vector_weight=0.7,
        fts_weight=0.3,
    ),
    "tag-only": SearchProfile(
        name="tag-only",
        description="Search primarily by tag similarity (requires tag index)",
        mode="hybrid",
        recency_weight=0.0,
        use_tag_index=True,
        tag_weight=0.8,
        vector_weight=0.7,
        fts_weight=0.3,
    ),
    "fresh-tags": SearchProfile(
        name="fresh-tags",
        description="Combine tag-heavy search with recency boost",
        mode="hybrid",
        recency_weight=0.3,
        use_tag_index=True,
        tag_weight=0.5,
        vector_weight=0.7,
        fts_weight=0.3,
    ),
}

# Default profile name
DEFAULT_PROFILE = "balanced"


def get_profile(name: str) -> Optional[SearchProfile]:
    """Get a search profile by name.

    Args:
        name: Profile name (case-insensitive).

    Returns:
        SearchProfile if found, None otherwise.
    """
    return BUILTIN_PROFILES.get(name.lower())


def list_profiles() -> List[SearchProfile]:
    """Get all available search profiles.

    Returns:
        List of all built-in profiles, sorted by name.
    """
    return sorted(BUILTIN_PROFILES.values(), key=lambda p: p.name)


def get_profile_names() -> List[str]:
    """Get names of all available profiles.

    Returns:
        Sorted list of profile names.
    """
    return sorted(BUILTIN_PROFILES.keys())


def format_profile_table() -> str:
    """Format profiles as a readable table for CLI output.

    Returns:
        Formatted table string.
    """
    lines = []
    lines.append("Available Search Profiles:")
    lines.append("-" * 70)
    lines.append(f"{'Name':<14} {'Mode':<8} {'Recency':<8} {'Tags':<6} Description")
    lines.append("-" * 70)

    for profile in list_profiles():
        tag_info = f"{profile.tag_weight:.1f}" if profile.use_tag_index else "-"
        lines.append(
            f"{profile.name:<14} "
            f"{profile.mode:<8} "
            f"{profile.recency_weight:<8.1f} "
            f"{tag_info:<6} "
            f"{profile.description}"
        )

    lines.append("-" * 70)
    lines.append(f"Default: {DEFAULT_PROFILE}")
    return "\n".join(lines)


def format_profile_detail(profile: SearchProfile) -> str:
    """Format a single profile with full details.

    Args:
        profile: The profile to format.

    Returns:
        Detailed formatted string.
    """
    lines = [
        f"Profile: {profile.name}",
        f"Description: {profile.description}",
        "",
        "Configuration:",
        f"  mode: {profile.mode}",
        f"  recency_weight: {profile.recency_weight}",
        f"  use_tag_index: {profile.use_tag_index}",
        f"  tag_weight: {profile.tag_weight}",
        f"  vector_weight: {profile.vector_weight}",
        f"  fts_weight: {profile.fts_weight}",
    ]
    return "\n".join(lines)
