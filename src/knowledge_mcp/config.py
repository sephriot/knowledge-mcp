"""Configuration management for knowledge storage."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Configuration for the knowledge storage."""

    data_path: Path

    def __post_init__(self) -> None:
        """Resolve relative paths to absolute paths."""
        if isinstance(self.data_path, str):
            self.data_path = Path(self.data_path)
        if not self.data_path.is_absolute():
            self.data_path = Path.cwd() / self.data_path

    @property
    def index_path(self) -> Path:
        """Path to the index.yaml file."""
        return self.data_path / "index.yaml"

    @property
    def index_path_json(self) -> Path:
        """Path to the legacy index.json file."""
        return self.data_path / "index.json"

    @property
    def atoms_path(self) -> Path:
        """Path to the atoms directory."""
        return self.data_path / "atoms"

    def ensure_dirs(self) -> None:
        """Ensure the storage directories exist."""
        self.atoms_path.mkdir(parents=True, exist_ok=True)


def create_config(data_path: str | None = None) -> Config:
    """Create config from CLI arg, env var, or default.

    Priority:
    1. CLI argument (data_path parameter)
    2. KNOWLEDGE_MCP_PATH environment variable
    3. Default: .knowledge
    """
    if not data_path:
        data_path = os.environ.get("KNOWLEDGE_MCP_PATH", ".knowledge")
    return Config(data_path=Path(data_path))


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = create_config()
    return _config


def set_config(cfg: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = cfg
