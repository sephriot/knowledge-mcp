"""Atom file storage management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from ..config import Config, get_config
from ..models.atom import Atom

if TYPE_CHECKING:
    pass


def _multiline_str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    """Represent multiline strings using literal block style (|)."""
    if "\n" in data:
        # Use literal block style for multiline strings
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


class _MultilineDumper(yaml.SafeDumper):
    """Custom YAML dumper that uses literal block style for multiline strings."""

    pass


_MultilineDumper.add_representer(str, _multiline_str_representer)


class AtomStorage:
    """Manages atom file storage."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or get_config()

    def _yaml_path(self, atom_id: str) -> Path:
        """Get the YAML path for an atom file."""
        return self.config.atoms_path / f"{atom_id}.yaml"

    def _json_path(self, atom_id: str) -> Path:
        """Get the legacy JSON path for an atom file."""
        return self.config.atoms_path / f"{atom_id}.json"

    def save(self, atom: Atom) -> Path:
        """Save atom to disk in YAML format.

        If a legacy JSON file exists, it is deleted after successful YAML write.
        """
        self.config.ensure_dirs()

        yaml_path = self._yaml_path(atom.id)
        json_path = self._json_path(atom.id)

        # Convert to dict and serialize as YAML
        data = atom.model_dump()
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                Dumper=_MultilineDumper,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        # Clean up legacy JSON file if it exists
        if json_path.exists():
            json_path.unlink(missing_ok=True)

        return yaml_path

    def load(self, atom_id: str) -> Atom | None:
        """Load atom from disk.

        Tries YAML first, falls back to JSON for backward compatibility.
        Returns None if atom doesn't exist.
        """
        yaml_path = self._yaml_path(atom_id)
        json_path = self._json_path(atom_id)

        # Try YAML first
        if yaml_path.exists():
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return Atom.model_validate(data)

        # Fall back to JSON
        if json_path.exists():
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            return Atom.model_validate(data)

        return None

    def delete(self, atom_id: str) -> bool:
        """Delete atom files from disk (both YAML and JSON).

        Returns True if any file was deleted, False otherwise.
        """
        yaml_path = self._yaml_path(atom_id)
        json_path = self._json_path(atom_id)

        deleted = False

        if yaml_path.exists():
            yaml_path.unlink()
            deleted = True
        if json_path.exists():
            json_path.unlink()
            deleted = True

        return deleted

    def exists(self, atom_id: str) -> bool:
        """Check if an atom file exists (YAML or JSON)."""
        return self._yaml_path(atom_id).exists() or self._json_path(atom_id).exists()

    def list_all_ids(self) -> list[str]:
        """List all atom IDs in storage."""
        if not self.config.atoms_path.exists():
            return []

        # Use a set to deduplicate IDs (in case both .yaml and .json exist)
        id_set: set[str] = set()

        for path in self.config.atoms_path.iterdir():
            if path.is_dir():
                continue
            name = path.name
            if not name.startswith("K-"):
                continue
            if name.endswith(".yaml"):
                id_set.add(name.removesuffix(".yaml"))
            elif name.endswith(".json"):
                id_set.add(name.removesuffix(".json"))

        return sorted(id_set)
