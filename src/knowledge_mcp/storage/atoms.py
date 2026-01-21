"""Atom file storage operations."""

import json
from pathlib import Path

from ..config import Config, get_config
from ..models.atom import Atom


class AtomStorage:
    """Manages atom file storage."""

    def __init__(self, config: Config | None = None):
        """Initialize the atom storage.

        Args:
            config: Configuration instance. Uses global config if not provided.
        """
        self._config = config or get_config()

    @property
    def config(self) -> Config:
        """Get the configuration."""
        return self._config

    def _get_atom_path(self, atom_id: str) -> Path:
        """Get the path for an atom file.

        Args:
            atom_id: The atom ID.

        Returns:
            Path to the atom file.
        """
        return self._config.atoms_path / f"{atom_id}.json"

    def save(self, atom: Atom) -> Path:
        """Save an atom to disk.

        Args:
            atom: The atom to save.

        Returns:
            Path to the saved atom file.
        """
        self._config.ensure_dirs()
        atom_path = self._get_atom_path(atom.id)

        with open(atom_path, "w", encoding="utf-8") as f:
            json.dump(atom.model_dump(), f, indent=2)

        return atom_path

    def load(self, atom_id: str) -> Atom | None:
        """Load an atom from disk.

        Args:
            atom_id: The ID of the atom to load.

        Returns:
            The loaded atom, or None if not found.
        """
        atom_path = self._get_atom_path(atom_id)
        if not atom_path.exists():
            return None

        with open(atom_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Atom.model_validate(data)

    def delete(self, atom_id: str) -> bool:
        """Delete an atom file from disk.

        Args:
            atom_id: The ID of the atom to delete.

        Returns:
            True if deleted, False if not found.
        """
        atom_path = self._get_atom_path(atom_id)
        if not atom_path.exists():
            return False

        atom_path.unlink()
        return True

    def exists(self, atom_id: str) -> bool:
        """Check if an atom file exists.

        Args:
            atom_id: The ID of the atom to check.

        Returns:
            True if the atom file exists.
        """
        return self._get_atom_path(atom_id).exists()

    def list_all_ids(self) -> list[str]:
        """List all atom IDs in storage.

        Returns:
            List of atom IDs.
        """
        atoms_path = self._config.atoms_path
        if not atoms_path.exists():
            return []

        return [p.stem for p in atoms_path.glob("K-*.json")]
