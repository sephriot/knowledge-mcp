"""Index model for fast atom lookup."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .enums import AtomStatus, AtomType, Confidence

if TYPE_CHECKING:
    from .atom import Atom


class IndexEntry(BaseModel):
    """Entry in the index for fast lookup."""

    id: str
    title: str
    type: AtomType
    status: AtomStatus
    confidence: Confidence
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    path: str
    updated_at: str
    popularity: int = 0  # Implicit retrieval counter

    model_config = {"use_enum_values": True}

    @classmethod
    def from_atom(cls, atom: Atom) -> IndexEntry:
        """Create an index entry from an atom."""
        return cls(
            id=atom.id,
            title=atom.title,
            type=atom.type,
            status=atom.status,
            confidence=atom.confidence,
            language=atom.language,
            tags=atom.tags,
            path=f"atoms/{atom.id}.yaml",
            updated_at=atom.updated_at,
        )


class Index(BaseModel):
    """Index of all knowledge atoms for fast lookup."""

    version: int = 1
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    atoms: list[IndexEntry] = Field(default_factory=list)

    def find_by_id(self, atom_id: str) -> IndexEntry | None:
        """Find an entry by ID."""
        for entry in self.atoms:
            if entry.id == atom_id:
                return entry
        return None

    def add_or_update(self, entry: IndexEntry) -> None:
        """Add or update an entry in the index."""
        for i, existing in enumerate(self.atoms):
            if existing.id == entry.id:
                entry.popularity = existing.popularity  # Preserve popularity
                self.atoms[i] = entry
                self.updated_at = datetime.now(timezone.utc).isoformat()
                return
        self.atoms.append(entry)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def remove(self, atom_id: str) -> bool:
        """Remove an entry from the index."""
        for i, entry in enumerate(self.atoms):
            if entry.id == atom_id:
                self.atoms.pop(i)
                self.updated_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def get_next_id(self) -> str:
        """Get the next available atom ID."""
        if not self.atoms:
            return "K-000001"

        max_num = 0
        for entry in self.atoms:
            if entry.id.startswith("K-"):
                try:
                    num = int(entry.id[2:])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        return f"K-{max_num + 1:06d}"
