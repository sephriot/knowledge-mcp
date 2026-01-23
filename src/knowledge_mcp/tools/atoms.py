"""Atom tools for knowledge management."""

from __future__ import annotations

from datetime import date
from typing import Any

from ..config import Config, get_config
from ..models.atom import Atom
from ..models.enums import AtomStatus
from ..models.index import IndexEntry
from ..storage.atoms import AtomStorage
from ..storage.index import IndexManager


def _atom_to_map(atom: Atom) -> dict[str, Any]:
    """Convert an atom to a dict for JSON response."""
    result: dict[str, Any] = {
        "id": atom.id,
        "title": atom.title,
        "type": atom.type,
        "status": atom.status,
        "confidence": atom.confidence,
        "content": {
            "summary": atom.content.summary,
            "details": atom.content.details,
            "pitfalls": atom.content.pitfalls,
            "update_notes": [
                {"date": n.date, "note": n.note} for n in atom.content.update_notes
            ],
        },
        "created_at": atom.created_at,
        "updated_at": atom.updated_at,
        "tags": atom.tags,
        "sources": [{"kind": s.kind, "ref": s.ref} for s in atom.sources],
        "links": [{"rel": l.rel, "id": l.id} for l in atom.links],
        "supersedes": atom.supersedes,
    }

    if atom.language:
        result["language"] = atom.language
    if atom.superseded_by:
        result["superseded_by"] = atom.superseded_by

    return result


class AtomTools:
    """Provides tools for managing knowledge atoms."""

    def __init__(
        self,
        config: Config | None = None,
        index_manager: IndexManager | None = None,
        atom_storage: AtomStorage | None = None,
    ) -> None:
        self.config = config or get_config()
        self.index_manager = index_manager or IndexManager(self.config)
        self.atom_storage = atom_storage or AtomStorage(self.config)

    def get_atom(self, id: str) -> dict[str, Any] | None:
        """Get full atom content by ID.

        Args:
            id: The atom ID (e.g., K-000001)

        Returns:
            Full atom content or None if not found
        """
        atom = self.atom_storage.load(id)
        if atom is None:
            return None
        return _atom_to_map(atom)

    def list_atoms(
        self,
        types: list[str] | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
        language: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List atoms with optional filtering.

        Args:
            types: Filter by atom types
            tags: Filter by tags (case-insensitive)
            status: Filter by status
            language: Filter by programming language
            limit: Maximum results (default 50)

        Returns:
            List of atom summaries
        """
        index = self.index_manager.get_index()

        # Convert types to set for fast lookup
        type_set = set(types) if types else set()

        results: list[dict[str, Any]] = []

        for entry in index.atoms:
            # Apply filters
            if type_set and entry.type not in type_set:
                continue
            if status and entry.status != status:
                continue
            if language and entry.language != language:
                continue
            if tags:
                entry_tags_lower = {t.lower() for t in entry.tags}
                if not any(t.lower() in entry_tags_lower for t in tags):
                    continue

            result: dict[str, Any] = {
                "id": entry.id,
                "title": entry.title,
                "type": entry.type,
                "status": entry.status,
                "confidence": entry.confidence,
                "tags": entry.tags,
                "updated_at": entry.updated_at,
            }
            if entry.language:
                result["language"] = entry.language

            results.append(result)

            if len(results) >= limit:
                break

        return results

    def delete_atom(self, id: str) -> dict[str, Any]:
        """Deprecate an atom (sets status to deprecated).

        Args:
            id: The atom ID to deprecate

        Returns:
            Result with success status
        """
        atom = self.atom_storage.load(id)
        if atom is None:
            return {
                "success": False,
                "error": f"Atom {id} not found",
            }

        # Set status to deprecated
        today = date.today().isoformat()
        atom.status = AtomStatus.DEPRECATED
        atom.updated_at = today

        # Save updated atom
        self.atom_storage.save(atom)

        # Update index
        entry = IndexEntry.from_atom(atom)
        self.index_manager.add_or_update(entry)

        return {
            "success": True,
            "message": f"Atom {id} deprecated",
        }

    def purge_atom(self, id: str) -> dict[str, Any]:
        """Permanently delete an atom from storage.

        WARNING: This cannot be undone. Use delete_atom to deprecate instead.

        Args:
            id: The atom ID to permanently delete

        Returns:
            Result with success status
        """
        if not self.atom_storage.exists(id):
            return {
                "success": False,
                "error": f"Atom {id} not found",
            }

        # Delete from storage
        self.atom_storage.delete(id)

        # Remove from index
        self.index_manager.remove(id)

        return {
            "success": True,
            "message": f"Atom {id} permanently deleted",
        }

    def list_all_ids(self) -> dict[str, Any]:
        """List all atom IDs in storage.

        Returns:
            Dictionary with list of IDs and count
        """
        ids = sorted(self.atom_storage.list_all_ids())
        return {
            "ids": ids,
            "count": len(ids),
        }

    def get_next_id(self) -> dict[str, Any]:
        """Get the next available atom ID.

        Returns:
            Dictionary with next_id field (e.g., K-000001)
        """
        next_id = self.index_manager.get_next_id()
        return {
            "next_id": next_id,
        }

    def export_all(self, format: str = "json") -> dict[str, Any]:
        """Export all knowledge as a single structure.

        Args:
            format: Export format (only "json" supported)

        Returns:
            All atoms in a single structure
        """
        if format != "json":
            return {
                "error": f"Unsupported format: {format}",
            }

        index = self.index_manager.get_index()
        atoms: list[dict[str, Any]] = []

        for entry in index.atoms:
            atom = self.atom_storage.load(entry.id)
            if atom is not None:
                atoms.append(_atom_to_map(atom))

        return {
            "version": 1,
            "exported_at": date.today().isoformat(),
            "count": len(atoms),
            "atoms": atoms,
        }

    def rebuild_index(self) -> dict[str, Any]:
        """Migrate JSON atoms to YAML and rebuild the index.

        Use this if the index gets out of sync with the atom files.

        Returns:
            Result with count of atoms indexed
        """
        index, migrated = self.index_manager.migrate_and_rebuild()

        result: dict[str, Any] = {
            "success": True,
            "atoms_indexed": len(index.atoms),
            "atoms_migrated": migrated,
        }

        if migrated > 0:
            result["message"] = (
                f"Migrated {migrated} atoms from JSON to YAML, "
                f"index rebuilt with {len(index.atoms)} atoms"
            )
        else:
            result["message"] = f"Index rebuilt with {len(index.atoms)} atoms"

        return result

    def get_summary(self, group_by: str = "type") -> dict[str, Any]:
        """Get summary of knowledge grouped by type, tag, or language.

        Args:
            group_by: Grouping criterion ("type", "tag", or "language")

        Returns:
            Summary with counts and items per group
        """
        index = self.index_manager.get_index()
        groups: dict[str, list[dict[str, Any]]] = {}

        for entry in index.atoms:
            if group_by == "type":
                key = entry.type
                groups.setdefault(key, []).append({
                    "id": entry.id,
                    "title": entry.title,
                    "status": entry.status,
                })
            elif group_by == "tag":
                for tag in entry.tags:
                    groups.setdefault(tag, []).append({
                        "id": entry.id,
                        "title": entry.title,
                        "type": entry.type,
                    })
            elif group_by == "language":
                key = entry.language if entry.language else "unspecified"
                groups.setdefault(key, []).append({
                    "id": entry.id,
                    "title": entry.title,
                    "type": entry.type,
                })
            else:
                return {
                    "error": f"Invalid group_by value: {group_by}",
                }

        # Build summary with counts
        groups_result: dict[str, Any] = {}
        for key, items in groups.items():
            groups_result[key] = {
                "count": len(items),
                "items": items,
            }

        return {
            "group_by": group_by,
            "total_atoms": len(index.atoms),
            "groups": groups_result,
        }
