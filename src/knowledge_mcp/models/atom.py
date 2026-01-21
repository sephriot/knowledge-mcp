"""Pydantic models for knowledge atoms."""

from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AtomType(str, Enum):
    """Type of knowledge atom."""

    FACT = "fact"
    DECISION = "decision"
    PROCEDURE = "procedure"
    PATTERN = "pattern"
    GOTCHA = "gotcha"
    GLOSSARY = "glossary"
    SNIPPET = "snippet"


class AtomStatus(str, Enum):
    """Status of a knowledge atom."""

    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class Confidence(str, Enum):
    """Confidence level of a knowledge atom."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Source(BaseModel):
    """Reference source for a knowledge atom."""

    kind: Literal["repo_path", "ticket", "url", "conversation"]
    ref: str

    model_config = {"extra": "forbid"}


class Link(BaseModel):
    """Link to another knowledge atom."""

    rel: Literal["depends_on", "see_also", "contradicts"]
    id: str

    model_config = {"extra": "forbid"}


class UpdateNote(BaseModel):
    """Note about an update to the atom."""

    date: str
    note: str

    model_config = {"extra": "forbid"}


class AtomContent(BaseModel):
    """Content of a knowledge atom."""

    summary: str
    details: str = ""
    pitfalls: list[str] = Field(default_factory=list)
    update_notes: list[UpdateNote] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class AtomContentInput(BaseModel):
    """Input content for upsert operations."""

    summary: str
    details: str | None = None
    pitfalls: list[str] | None = None
    update_notes: list[UpdateNote] | None = None

    model_config = {"extra": "forbid"}


class Atom(BaseModel):
    """A knowledge atom - the fundamental unit of knowledge storage."""

    id: str = Field(pattern=r"^K-\d{6}$")
    title: str
    type: AtomType
    status: AtomStatus
    confidence: Confidence
    content: AtomContent
    language: str | None = None
    created_at: str  # ISO date string (YYYY-MM-DD)
    updated_at: str  # ISO date string (YYYY-MM-DD)
    tags: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str | None = None

    model_config = {"extra": "forbid"}


class IndexEntry(BaseModel):
    """Entry in the index for fast lookup."""

    id: str
    title: str
    type: AtomType
    status: AtomStatus
    confidence: Confidence
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    path: str  # Relative path to atom file
    updated_at: str

    model_config = {"extra": "forbid"}

    @classmethod
    def from_atom(cls, atom: Atom) -> "IndexEntry":
        """Create an index entry from an atom."""
        return cls(
            id=atom.id,
            title=atom.title,
            type=atom.type,
            status=atom.status,
            confidence=atom.confidence,
            language=atom.language,
            tags=atom.tags,
            path=f"atoms/{atom.id}.json",
            updated_at=atom.updated_at,
        )


class Index(BaseModel):
    """Index of all knowledge atoms for fast lookup."""

    version: int = 1
    updated_at: str  # ISO datetime string
    atoms: list[IndexEntry] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @classmethod
    def create_empty(cls) -> "Index":
        """Create a new empty index."""
        return cls(
            version=1,
            updated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            atoms=[],
        )

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
                self.atoms[i] = entry
                self.updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                return
        self.atoms.append(entry)
        self.updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def remove(self, atom_id: str) -> bool:
        """Remove an entry from the index."""
        for i, entry in enumerate(self.atoms):
            if entry.id == atom_id:
                del self.atoms[i]
                self.updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                return True
        return False

    def get_next_id(self) -> str:
        """Get the next available atom ID."""
        if not self.atoms:
            return "K-000001"

        # Find the highest ID number
        max_num = 0
        for entry in self.atoms:
            num = int(entry.id.split("-")[1])
            if num > max_num:
                max_num = num

        return f"K-{max_num + 1:06d}"
