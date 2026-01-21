"""Atom management tool implementations."""

from datetime import date
from collections import defaultdict

from ..config import Config, get_config
from ..models.atom import AtomStatus, AtomType, IndexEntry
from ..storage.atoms import AtomStorage
from ..storage.index import IndexManager


class AtomTools:
    """Tools for managing knowledge atoms."""

    def __init__(self, config: Config | None = None):
        """Initialize the atom tools.

        Args:
            config: Configuration instance. Uses global config if not provided.
        """
        self._config = config or get_config()
        self._index_manager = IndexManager(self._config)
        self._atom_storage = AtomStorage(self._config)

    def get_atom(self, id: str) -> dict | None:
        """Get full atom content by ID.

        Args:
            id: The atom ID.

        Returns:
            The full atom as a dictionary, or None if not found.
        """
        atom = self._atom_storage.load(id)
        if atom is None:
            return None
        return atom.model_dump()

    def list_atoms(
        self,
        types: list[str] | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
        language: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List atoms with optional filtering.

        Args:
            types: Filter by atom types.
            tags: Filter by tags.
            status: Filter by status.
            language: Filter by language.
            limit: Maximum number of results.

        Returns:
            List of atom summaries.
        """
        index = self._index_manager.get_index()

        # Convert types to enum values
        type_enums: set[AtomType] | None = None
        if types:
            type_enums = {AtomType(t) for t in types}

        # Convert status to enum
        status_enum: AtomStatus | None = None
        if status:
            status_enum = AtomStatus(status)

        results = []
        for entry in index.atoms:
            # Apply filters
            if type_enums and entry.type not in type_enums:
                continue
            if status_enum and entry.status != status_enum:
                continue
            if language and entry.language != language:
                continue
            if tags:
                entry_tags_lower = {t.lower() for t in entry.tags}
                if not any(tag.lower() in entry_tags_lower for tag in tags):
                    continue

            results.append({
                "id": entry.id,
                "title": entry.title,
                "type": entry.type.value,
                "status": entry.status.value,
                "confidence": entry.confidence.value,
                "language": entry.language,
                "tags": entry.tags,
                "updated_at": entry.updated_at,
            })

            if len(results) >= limit:
                break

        return results

    def delete_atom(self, id: str) -> dict:
        """Deprecate an atom (set status to deprecated).

        Args:
            id: The atom ID.

        Returns:
            Result message.
        """
        atom = self._atom_storage.load(id)
        if atom is None:
            return {"success": False, "error": f"Atom {id} not found"}

        # Set status to deprecated instead of deleting
        today = date.today().isoformat()
        atom.status = AtomStatus.DEPRECATED
        atom.updated_at = today

        # Save updated atom
        self._atom_storage.save(atom)

        # Update index
        entry = IndexEntry.from_atom(atom)
        self._index_manager.add_or_update(entry)

        return {"success": True, "message": f"Atom {id} deprecated"}

    def purge_atom(self, id: str) -> dict:
        """Permanently delete an atom from storage.

        Args:
            id: The atom ID.

        Returns:
            Result message.
        """
        if not self._atom_storage.exists(id):
            return {"success": False, "error": f"Atom {id} not found"}

        # Delete from storage
        self._atom_storage.delete(id)

        # Remove from index
        self._index_manager.remove(id)

        return {"success": True, "message": f"Atom {id} permanently deleted"}

    def list_all_ids(self) -> dict:
        """List all atom IDs in storage.

        Returns:
            Dictionary with list of IDs and count.
        """
        ids = self._atom_storage.list_all_ids()
        return {"ids": sorted(ids), "count": len(ids)}

    def get_next_id(self) -> dict:
        """Get the next available atom ID.

        Returns:
            Dictionary with the next ID.
        """
        next_id = self._index_manager.get_next_id()
        return {"next_id": next_id}

    def export_all(self, format: str = "json") -> dict:
        """Export all knowledge as a single structure.

        Args:
            format: Export format (only "json" supported).

        Returns:
            All atoms as a dictionary.
        """
        if format != "json":
            return {"error": f"Unsupported format: {format}"}

        index = self._index_manager.get_index()
        atoms = []

        for entry in index.atoms:
            atom = self._atom_storage.load(entry.id)
            if atom:
                atoms.append(atom.model_dump())

        return {
            "version": 1,
            "exported_at": date.today().isoformat(),
            "count": len(atoms),
            "atoms": atoms,
        }

    def rebuild_index(self) -> dict:
        """Rebuild index.json from atom files.

        Returns:
            Result with count of atoms indexed.
        """
        index = self._index_manager.rebuild_from_atoms(self._config.atoms_path)
        return {
            "success": True,
            "count": len(index.atoms),
            "message": f"Index rebuilt with {len(index.atoms)} atoms",
        }

    def get_summary(self, group_by: str = "type") -> dict:
        """Get summary of knowledge grouped by type, tag, or language.

        Args:
            group_by: Grouping criterion ("type", "tag", or "language").

        Returns:
            Summary grouped by the specified criterion.
        """
        index = self._index_manager.get_index()
        groups: dict[str, list[dict]] = defaultdict(list)

        for entry in index.atoms:
            if group_by == "type":
                key = entry.type.value
                groups[key].append({
                    "id": entry.id,
                    "title": entry.title,
                    "status": entry.status.value,
                })
            elif group_by == "tag":
                for tag in entry.tags:
                    groups[tag].append({
                        "id": entry.id,
                        "title": entry.title,
                        "type": entry.type.value,
                    })
            elif group_by == "language":
                key = entry.language or "unspecified"
                groups[key].append({
                    "id": entry.id,
                    "title": entry.title,
                    "type": entry.type.value,
                })
            else:
                return {"error": f"Invalid group_by value: {group_by}"}

        # Build summary with counts
        summary = {
            "group_by": group_by,
            "total_atoms": len(index.atoms),
            "groups": {
                key: {"count": len(items), "items": items}
                for key, items in sorted(groups.items())
            },
        }

        return summary
