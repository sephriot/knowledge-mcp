"""Configuration for the Knowledge MCP Server."""

import os
from pathlib import Path


class Config:
    """Configuration for the knowledge storage."""

    def __init__(self, data_path: Path | str | None = None):
        """Initialize configuration.

        Args:
            data_path: Path to the knowledge storage directory.
                       Defaults to KNOWLEDGE_MCP_PATH env var or ".knowledge".
        """
        if data_path is None:
            data_path = os.environ.get("KNOWLEDGE_MCP_PATH", ".knowledge")
        self._data_path = Path(data_path)

    @property
    def data_path(self) -> Path:
        """Path to the knowledge storage directory."""
        return self._data_path

    @property
    def index_path(self) -> Path:
        """Path to the index.json file."""
        return self._data_path / "index.json"

    @property
    def atoms_path(self) -> Path:
        """Path to the atoms directory."""
        return self._data_path / "atoms"

    def ensure_dirs(self) -> None:
        """Ensure the storage directories exist."""
        self.atoms_path.mkdir(parents=True, exist_ok=True)


# Global config instance (can be overridden)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
