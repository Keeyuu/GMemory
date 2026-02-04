import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)


# Default configuration templates for common use cases
CONFIG_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "default": {
        "description": "Default balanced configuration",
        "storage": {"db_path": "~/.gmemory/data.db"},
        "embedding": {
            "provider": "fastembed",
            "model": "nomic",
            "dimension": 768,
        },
        "search": {
            "default_mode": "hybrid",
            "vector_weight": 0.7,
            "fts_weight": 0.3,
        },
    },
    "minimal": {
        "description": "Minimal footprint - smaller model, less storage",
        "storage": {"db_path": "~/.gmemory/data.db"},
        "embedding": {
            "provider": "fastembed",
            "model": "all-minilm",
            "dimension": 384,
        },
        "search": {
            "default_mode": "hybrid",
            "vector_weight": 0.6,
            "fts_weight": 0.4,
        },
    },
    "semantic-heavy": {
        "description": "Prioritize semantic search over keyword matching",
        "storage": {"db_path": "~/.gmemory/data.db"},
        "embedding": {
            "provider": "fastembed",
            "model": "nomic",
            "dimension": 768,
        },
        "search": {
            "default_mode": "hybrid",
            "vector_weight": 0.85,
            "fts_weight": 0.15,
            "recency_weight": 0.1,
        },
    },
    "recent-focused": {
        "description": "Favor recent memories in search results",
        "storage": {"db_path": "~/.gmemory/data.db"},
        "embedding": {
            "provider": "fastembed",
            "model": "nomic",
            "dimension": 768,
        },
        "search": {
            "default_mode": "hybrid",
            "vector_weight": 0.5,
            "fts_weight": 0.2,
            "recency_weight": 0.3,
            "recency_window_days": 30,
        },
    },
    "project-isolated": {
        "description": "Per-project database isolation template",
        "storage": {"db_path": "{project}/.gmemory/data.db"},
        "embedding": {
            "provider": "fastembed",
            "model": "nomic",
            "dimension": 768,
        },
        "search": {
            "default_mode": "hybrid",
            "vector_weight": 0.7,
            "fts_weight": 0.3,
        },
        "project": {
            "isolation_mode": "database",  # database, filter, none
            "auto_detect_root": True,
        },
    },
}


class Config:
    """
    Configuration manager for GMemory.
    Supports loading from default values, in-repo config.toml, and ~/.gmemory/config.toml.
    Also supports project-specific configuration overrides.
    """

    def __init__(self, project_path: Optional[str] = None) -> None:
        self._config: Dict[str, Any] = {
            "storage": {
                "db_path": "~/.gmemory/data.db",
            },
            "embedding": {
                "provider": "fastembed",
                "model": "nomic",
                "dimension": 768,
                "cache_dir": "~/.gmemory/models",
                "profiles": {
                    "nomic": {
                        "provider": "fastembed",
                        "model": "nomic",
                        "dimension": 768,
                    },
                    "bge-small": {
                        "provider": "fastembed",
                        "model": "bge-small",
                        "dimension": 384,
                    },
                    "bge-base": {
                        "provider": "fastembed",
                        "model": "bge-base",
                        "dimension": 768,
                    },
                    "all-minilm": {
                        "provider": "fastembed",
                        "model": "all-minilm",
                        "dimension": 384,
                    },
                },
                "active_profile": "nomic",
            },
            "scanner": {
                "default_agent": "opencode",
            },
            "search": {
                "default_mode": "hybrid",
                "default_profile": "balanced",
                "default_limit": 10,
                "vector_weight": 0.7,
                "fts_weight": 0.3,
                "recency_weight": 0.0,
                "recency_window_days": 90,
                "min_score_threshold": 0.2,
                "use_tag_index": False,
                "tag_weight": 0.3,
            },
            "lifecycle": {
                "retention_days": 0,  # 0 = no auto-purge
                "archive_before_purge": True,
                "auto_compact_threshold": 1000,  # compact after N deletes
            },
            "project": {
                "isolation_mode": "none",  # none, filter, database
                "auto_detect_root": False,
                "default_project": None,
            },
        }
        self._project_path = project_path
        self._project_config_loaded = False
        self.load()

    def load(self) -> None:
        """Loads configuration from multiple sources in priority order."""
        # 1. Look for config.toml in repo root
        repo_config = Path("config.toml")
        if repo_config.exists():
            self._update_from_file(repo_config)

        # 2. Look for config.toml in ~/.gmemory/config.toml
        home_config = Path.home() / ".gmemory" / "config.toml"
        if home_config.exists():
            self._update_from_file(home_config)

        # 3. Load project-specific config if project_path is set
        if self._project_path:
            self._load_project_config(self._project_path)

    def _load_project_config(self, project_path: str) -> None:
        """Load project-specific configuration overrides.

        Looks for .gmemory/config.toml in the project directory.
        """
        project_dir = Path(project_path)
        if not project_dir.is_dir():
            project_dir = project_dir.parent

        project_config = project_dir / ".gmemory" / "config.toml"
        if project_config.exists():
            self._update_from_file(project_config)
            self._project_config_loaded = True
            logger.debug(f"Loaded project config from {project_config}")

    def _update_from_file(self, path: Path) -> None:
        if tomllib is None:
            logger.debug("TOML parser not available, skipping config file")
            return

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
                self._deep_update(self._config, data)
                logger.debug(f"Loaded config from {path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {path}: {e}")

    def _deep_update(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation (e.g., 'storage.db_path')."""
        parts = key.split(".")
        val = self._config
        for part in parts:
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                return default
        return val

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation (runtime only)."""
        parts = key.split(".")
        target = self._config
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    @property
    def db_path(self) -> Path:
        path = self.get("storage.db_path")
        # Support {project} placeholder for project-isolated databases
        if "{project}" in path and self._project_path:
            path = path.replace("{project}", self._project_path)
        return Path(os.path.expanduser(path))

    @property
    def embedding_provider(self) -> str:
        return str(self.get("embedding.provider"))

    @property
    def embedding_model(self) -> str:
        return str(self.get("embedding.model"))

    @property
    def embedding_dimension(self) -> int:
        return int(self.get("embedding.dimension"))

    @property
    def embedding_cache_dir(self) -> Optional[str]:
        cache_dir = self.get("embedding.cache_dir")
        if cache_dir:
            return os.path.expanduser(cache_dir)
        return None

    @property
    def default_agent(self) -> str:
        return str(self.get("scanner.default_agent"))

    # Search configuration properties
    @property
    def search_default_mode(self) -> str:
        return str(self.get("search.default_mode", "hybrid"))

    @property
    def search_default_profile(self) -> str:
        return str(self.get("search.default_profile", "balanced"))

    @property
    def search_default_limit(self) -> int:
        return int(self.get("search.default_limit", 10))

    @property
    def search_vector_weight(self) -> float:
        return float(self.get("search.vector_weight", 0.7))

    @property
    def search_fts_weight(self) -> float:
        return float(self.get("search.fts_weight", 0.3))

    @property
    def search_recency_weight(self) -> float:
        return float(self.get("search.recency_weight", 0.0))

    @property
    def search_recency_window_days(self) -> int:
        return int(self.get("search.recency_window_days", 90))

    @property
    def search_min_score_threshold(self) -> float:
        return float(self.get("search.min_score_threshold", 0.2))

    @property
    def search_use_tag_index(self) -> bool:
        return bool(self.get("search.use_tag_index", False))

    @property
    def search_tag_weight(self) -> float:
        return float(self.get("search.tag_weight", 0.3))

    # Lifecycle configuration properties
    @property
    def lifecycle_retention_days(self) -> int:
        return int(self.get("lifecycle.retention_days", 0))

    @property
    def lifecycle_archive_before_purge(self) -> bool:
        return bool(self.get("lifecycle.archive_before_purge", True))

    @property
    def lifecycle_auto_compact_threshold(self) -> int:
        return int(self.get("lifecycle.auto_compact_threshold", 1000))

    # Project isolation properties
    @property
    def project_isolation_mode(self) -> str:
        return str(self.get("project.isolation_mode", "none"))

    @property
    def project_auto_detect_root(self) -> bool:
        return bool(self.get("project.auto_detect_root", False))

    @property
    def project_default(self) -> Optional[str]:
        return self.get("project.default_project")

    @property
    def project_config_loaded(self) -> bool:
        return self._project_config_loaded

    # Embedding profile properties
    @property
    def embedding_profiles(self) -> Dict[str, Any]:
        """Get all available embedding profiles."""
        return dict(self.get("embedding.profiles", {}))

    @property
    def embedding_active_profile(self) -> str:
        """Get the currently active embedding profile name."""
        return str(self.get("embedding.active_profile", "nomic"))

    def get_embedding_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific embedding profile by name."""
        profiles = self.embedding_profiles
        return profiles.get(name)

    def set_embedding_profile(self, name: str) -> bool:
        """Set the active embedding profile (runtime only, doesn't persist).

        To persist, update config.toml manually.
        """
        if name not in self.embedding_profiles:
            return False
        self._config["embedding"]["active_profile"] = name
        profile = self.embedding_profiles[name]
        # Update active embedding settings
        self._config["embedding"]["provider"] = profile.get("provider", "fastembed")
        self._config["embedding"]["model"] = profile.get("model", name)
        self._config["embedding"]["dimension"] = profile.get("dimension", 768)
        return True

    def with_project(self, project_path: str) -> "Config":
        """Create a new Config instance with project-specific overrides.

        Args:
            project_path: Path to the project directory.

        Returns:
            New Config instance with project config loaded.
        """
        return Config(project_path=project_path)


def get_config_templates() -> Dict[str, Dict[str, Any]]:
    """Get all available configuration templates.

    Returns:
        Dict mapping template names to their configurations.
    """
    return CONFIG_TEMPLATES.copy()


def get_template(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific configuration template.

    Args:
        name: Template name.

    Returns:
        Template configuration dict or None if not found.
    """
    return CONFIG_TEMPLATES.get(name)


def list_templates() -> List[Dict[str, str]]:
    """List all available templates with descriptions.

    Returns:
        List of dicts with name and description.
    """
    return [
        {"name": name, "description": tpl.get("description", "")}
        for name, tpl in CONFIG_TEMPLATES.items()
    ]


def generate_config_file(
    template: str = "default",
    output_path: Optional[str] = None,
    project_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a configuration file from a template.

    Args:
        template: Template name to use.
        output_path: Path to write the config file. If None, returns content.
        project_path: If provided, generates project-specific config.

    Returns:
        Dict with result status and content/path.
    """
    tpl = get_template(template)
    if not tpl:
        return {
            "error": f"Unknown template: '{template}'",
            "available": list(CONFIG_TEMPLATES.keys()),
        }

    # Generate TOML content
    lines = [
        f"# GMemory Configuration",
        f"# Generated from template: {template}",
        f"# {tpl.get('description', '')}",
        "",
    ]

    def format_section(data: Dict[str, Any], prefix: str = "") -> List[str]:
        result = []
        for key, value in data.items():
            if key == "description":
                continue
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.append(f"[{full_key}]")
                for k, v in value.items():
                    if isinstance(v, dict):
                        # Nested section
                        result.extend(format_section({k: v}, full_key))
                    else:
                        result.append(f"{k} = {_format_toml_value(v)}")
                result.append("")
            else:
                result.append(f"{key} = {_format_toml_value(value)}")
        return result

    lines.extend(format_section(tpl))
    content = "\n".join(lines)

    if output_path:
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "path": str(path.absolute()),
                "template": template,
                "message": f"Configuration written to {path}",
            }
        except Exception as e:
            return {"error": f"Failed to write config: {e}"}

    return {
        "success": True,
        "template": template,
        "content": content,
    }


def _format_toml_value(value: Any) -> str:
    """Format a value for TOML output."""
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, (int, float)):
        return str(value)
    elif value is None:
        return '""'
    else:
        return f'"{value}"'


def init_project_config(
    project_path: str,
    template: str = "default",
    force: bool = False,
) -> Dict[str, Any]:
    """Initialize project-specific configuration.

    Creates a .gmemory/config.toml in the project directory.

    Args:
        project_path: Path to the project directory.
        template: Template to use for initial config.
        force: If True, overwrite existing config.

    Returns:
        Dict with result status.
    """
    project_dir = Path(project_path)
    if not project_dir.is_dir():
        return {"error": f"Not a directory: {project_path}"}

    config_dir = project_dir / ".gmemory"
    config_file = config_dir / "config.toml"

    if config_file.exists() and not force:
        return {
            "error": "Project config already exists",
            "path": str(config_file),
            "hint": "Use --force to overwrite",
        }

    return generate_config_file(
        template=template,
        output_path=str(config_file),
        project_path=project_path,
    )


# Global config instance
config = Config()
