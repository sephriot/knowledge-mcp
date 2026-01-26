"""Index management with thread safety."""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import yaml

from ..config import Config, get_config
from ..models.index import Index, IndexEntry
from .atoms import AtomStorage


class IndexManager:
    """Manages the knowledge index file with thread-safe operations."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or get_config()
        self._index: Index | None = None
        self._lock = threading.RLock()

    def _load_locked(self) -> None:
        """Load index from disk. Caller must hold the lock.

        Tries YAML first, falls back to JSON for backward compatibility.
        """
        if self._index is not None:
            return

        index_path = self.config.index_path
        index_path_json = self.config.index_path_json

        # Try YAML first
        if index_path.exists():
            with open(index_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self._index = Index.model_validate(data)
            return

        # Fall back to JSON
        if index_path_json.exists():
            with open(index_path_json, encoding="utf-8") as f:
                data = json.load(f)
            self._index = Index.model_validate(data)
            return

        # Create empty index
        self._index = Index()

    def _save_locked(self) -> None:
        """Save index to disk in YAML format. Caller must hold the lock.

        If a legacy JSON index file exists, it is deleted.
        """
        if self._index is None:
            return

        self.config.ensure_dirs()

        index_path = self.config.index_path
        index_path_json = self.config.index_path_json

        # Sort atoms by ID for deterministic output
        sorted_index = self._index.model_copy()
        sorted_index.atoms = sorted(sorted_index.atoms, key=lambda e: e.id)
        data = sorted_index.model_dump()
        with open(index_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Clean up legacy JSON index file if it exists
        if index_path_json.exists():
            index_path_json.unlink(missing_ok=True)

    def get_index(self) -> Index:
        """Get the current index, loading if necessary."""
        with self._lock:
            self._load_locked()
            assert self._index is not None
            return self._index

    def add_or_update(self, entry: IndexEntry) -> None:
        """Add or update an entry in the index."""
        with self._lock:
            self._load_locked()
            assert self._index is not None
            self._index.add_or_update(entry)
            self._save_locked()

    def remove(self, atom_id: str) -> bool:
        """Remove an entry from the index."""
        with self._lock:
            self._load_locked()
            assert self._index is not None
            result = self._index.remove(atom_id)
            if result:
                self._save_locked()
            return result

    def find_by_id(self, atom_id: str) -> IndexEntry | None:
        """Find an entry by ID."""
        with self._lock:
            self._load_locked()
            assert self._index is not None
            return self._index.find_by_id(atom_id)

    def increment_popularity(self, atom_id: str) -> bool:
        """Increment popularity counter for an atom (thread-safe).

        Persistence depends on config.persist_popularity setting.

        Args:
            atom_id: The atom ID to increment popularity for

        Returns:
            True if atom was found and incremented, False otherwise
        """
        with self._lock:
            self._load_locked()
            assert self._index is not None
            entry = self._index.find_by_id(atom_id)
            if entry is None:
                return False
            entry.popularity += 1
            if self.config.persist_popularity:
                self._save_locked()
            return True

    def get_next_id(self) -> str:
        """Get the next available atom ID."""
        with self._lock:
            self._load_locked()
            assert self._index is not None
            return self._index.get_next_id()

    def rebuild_from_atoms(self) -> Index:
        """Rebuild the index from atom files."""
        with self._lock:
            self._index = Index()
            storage = AtomStorage(self.config)

            atoms_path = self.config.atoms_path
            if not atoms_path.exists():
                self._save_locked()
                return self._index

            # Collect unique atom IDs
            id_set: set[str] = set()
            for path in atoms_path.iterdir():
                if path.is_dir():
                    continue
                name = path.name
                if not name.startswith("K-"):
                    continue
                if name.endswith(".yaml"):
                    id_set.add(name.removesuffix(".yaml"))
                elif name.endswith(".json"):
                    id_set.add(name.removesuffix(".json"))

            load_errors: list[str] = []
            for atom_id in id_set:
                try:
                    atom = storage.load(atom_id)
                    if atom is not None:
                        index_entry = IndexEntry.from_atom(atom)
                        self._index.add_or_update(index_entry)
                except Exception as e:
                    load_errors.append(f"{atom_id}: {e}")

            # Log any errors to stderr (MCP uses stdout for communication)
            if load_errors:
                print(
                    f"Warning: failed to load {len(load_errors)} atoms during rebuild:",
                    file=sys.stderr,
                )
                for error in load_errors:
                    print(f"  - {error}", file=sys.stderr)

            self._save_locked()
            return self._index

    def migrate_and_rebuild(self) -> tuple[Index, int]:
        """Migrate all JSON atoms to YAML and rebuild the index.

        Returns:
            Tuple of (rebuilt index, number of atoms migrated)
        """
        storage = AtomStorage(self.config)
        atoms_path = self.config.atoms_path

        migrated = 0

        if atoms_path.exists():
            # Collect all JSON files that need migration
            for path in atoms_path.iterdir():
                if path.is_dir():
                    continue
                name = path.name
                if not name.startswith("K-") or not name.endswith(".json"):
                    continue

                atom_id = name.removesuffix(".json")
                yaml_path = atoms_path / f"{atom_id}.yaml"

                # Skip if YAML already exists
                if yaml_path.exists():
                    continue

                # Load from JSON (will use JSON since YAML doesn't exist)
                try:
                    atom = storage.load(atom_id)
                    if atom is None:
                        continue
                    # Save as YAML (this also deletes the JSON file)
                    storage.save(atom)
                    migrated += 1
                except Exception as e:
                    print(f"Warning: failed to migrate {atom_id}: {e}", file=sys.stderr)

        # Now rebuild the index
        index = self.rebuild_from_atoms()
        return index, migrated

    def invalidate_cache(self) -> None:
        """Invalidate the cached index."""
        with self._lock:
            self._index = None
