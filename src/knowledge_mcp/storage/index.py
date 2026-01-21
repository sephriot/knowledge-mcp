"""Index management for knowledge atoms."""

import json
from pathlib import Path

from ..config import Config, get_config
from ..models.atom import Index, IndexEntry


class IndexManager:
    """Manages the knowledge index file."""

    def __init__(self, config: Config | None = None):
        """Initialize the index manager.

        Args:
            config: Configuration instance. Uses global config if not provided.
        """
        self._config = config or get_config()
        self._index: Index | None = None

    @property
    def config(self) -> Config:
        """Get the configuration."""
        return self._config

    def load(self) -> Index:
        """Load the index from disk.

        Returns:
            The loaded index, or an empty index if it doesn't exist.
        """
        if self._index is not None:
            return self._index

        index_path = self._config.index_path
        if not index_path.exists():
            self._index = Index.create_empty()
            return self._index

        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._index = Index.model_validate(data)
            return self._index

    def save(self) -> None:
        """Save the index to disk."""
        if self._index is None:
            return

        self._config.ensure_dirs()
        index_path = self._config.index_path

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(self._index.model_dump(), f, indent=2)

    def get_index(self) -> Index:
        """Get the current index, loading if necessary."""
        if self._index is None:
            return self.load()
        return self._index

    def add_or_update(self, entry: IndexEntry) -> None:
        """Add or update an entry in the index.

        Args:
            entry: The index entry to add or update.
        """
        index = self.get_index()
        index.add_or_update(entry)
        self.save()

    def remove(self, atom_id: str) -> bool:
        """Remove an entry from the index.

        Args:
            atom_id: The ID of the atom to remove.

        Returns:
            True if the entry was removed, False if not found.
        """
        index = self.get_index()
        result = index.remove(atom_id)
        if result:
            self.save()
        return result

    def find_by_id(self, atom_id: str) -> IndexEntry | None:
        """Find an entry by ID.

        Args:
            atom_id: The ID to search for.

        Returns:
            The index entry if found, None otherwise.
        """
        index = self.get_index()
        return index.find_by_id(atom_id)

    def get_next_id(self) -> str:
        """Get the next available atom ID.

        Returns:
            The next available ID in K-XXXXXX format.
        """
        index = self.get_index()
        return index.get_next_id()

    def rebuild_from_atoms(self, atoms_path: Path) -> Index:
        """Rebuild the index from atom files.

        Args:
            atoms_path: Path to the atoms directory.

        Returns:
            The rebuilt index.
        """
        from .atoms import AtomStorage

        self._index = Index.create_empty()

        if not atoms_path.exists():
            self.save()
            return self._index

        storage = AtomStorage(self._config)

        for atom_file in atoms_path.glob("K-*.json"):
            atom = storage.load(atom_file.stem)
            if atom is not None:
                entry = IndexEntry.from_atom(atom)
                self._index.add_or_update(entry)

        self.save()
        return self._index

    def invalidate_cache(self) -> None:
        """Invalidate the cached index, forcing a reload on next access."""
        self._index = None
