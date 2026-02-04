import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager for GMemory.
    Supports loading from default values, in-repo config.toml, and ~/.gmemory/config.toml.
    """

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {
            "storage": {
                "db_path": "~/.gmemory/data.db",
            },
            "embedding": {
                "provider": "fastembed",
                "model": "nomic",
                "dimension": 768,
                "cache_dir": "~/.gmemory/models",
            },
            "scanner": {
                "default_agent": "opencode",
            },
        }
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

    @property
    def db_path(self) -> Path:
        path = self.get("storage.db_path")
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


# Global config instance
config = Config()
