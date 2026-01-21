"""Upsert tool implementation."""

from datetime import date

from ..config import Config, get_config
from ..models.atom import (
    Atom,
    AtomContent,
    AtomStatus,
    AtomType,
    Confidence,
    IndexEntry,
    Link,
    Source,
    UpdateNote,
)
from ..storage.atoms import AtomStorage
from ..storage.index import IndexManager


class UpsertHandler:
    """Handler for upserting knowledge atoms."""

    def __init__(self, config: Config | None = None):
        """Initialize the upsert handler.

        Args:
            config: Configuration instance. Uses global config if not provided.
        """
        self._config = config or get_config()
        self._index_manager = IndexManager(self._config)
        self._atom_storage = AtomStorage(self._config)

    def upsert(
        self,
        title: str,
        type: str,
        status: str,
        confidence: str,
        content: dict,
        id: str | None = None,
        language: str | None = None,
        tags: list[str] | None = None,
        sources: list[dict] | None = None,
        links: list[dict] | None = None,
    ) -> dict:
        """Create or update a knowledge atom.

        Args:
            title: Short descriptive title.
            type: Atom type (fact, decision, procedure, pattern, gotcha, glossary, snippet).
            status: Status (active, draft, deprecated).
            confidence: Confidence level (high, medium, low).
            content: Content object with summary, details, pitfalls, update_notes.
            id: Optional ID for updates. If not provided, creates a new atom.
            language: Optional programming language.
            tags: Optional list of tags.
            sources: Optional list of source references.
            links: Optional list of links to other atoms.

        Returns:
            The created/updated atom as a dictionary.
        """
        today = date.today().isoformat()

        # Handle existing atom update
        if id:
            existing = self._atom_storage.load(id)
            if existing:
                return self._update_atom(
                    existing,
                    title=title,
                    type=type,
                    status=status,
                    confidence=confidence,
                    content=content,
                    language=language,
                    tags=tags,
                    sources=sources,
                    links=links,
                )

        # Create new atom
        if id is None:
            id = self._index_manager.get_next_id()

        # Build content object
        atom_content = AtomContent(
            summary=content.get("summary", ""),
            details=content.get("details", ""),
            pitfalls=content.get("pitfalls", []),
            update_notes=[
                UpdateNote(**note) if isinstance(note, dict) else note
                for note in content.get("update_notes", [])
            ],
        )

        # Add initial update note if none provided
        if not atom_content.update_notes:
            atom_content.update_notes.append(
                UpdateNote(date=today, note="Initial creation")
            )

        # Build atom
        atom = Atom(
            id=id,
            title=title,
            type=AtomType(type),
            status=AtomStatus(status),
            confidence=Confidence(confidence),
            content=atom_content,
            language=language,
            created_at=today,
            updated_at=today,
            tags=tags or [],
            sources=[Source(**s) for s in (sources or [])],
            links=[Link(**ln) for ln in (links or [])],
        )

        # Save atom and update index
        self._atom_storage.save(atom)
        entry = IndexEntry.from_atom(atom)
        self._index_manager.add_or_update(entry)

        return atom.model_dump()

    def _update_atom(
        self,
        existing: Atom,
        title: str,
        type: str,
        status: str,
        confidence: str,
        content: dict,
        language: str | None = None,
        tags: list[str] | None = None,
        sources: list[dict] | None = None,
        links: list[dict] | None = None,
    ) -> dict:
        """Update an existing atom.

        Args:
            existing: The existing atom to update.
            title: New title.
            type: New type.
            status: New status.
            confidence: New confidence.
            content: New content.
            language: New language.
            tags: New tags.
            sources: New sources.
            links: New links.

        Returns:
            The updated atom as a dictionary.
        """
        today = date.today().isoformat()

        # Build content object
        update_notes = [
            UpdateNote(**note) if isinstance(note, dict) else note
            for note in content.get("update_notes", [])
        ]

        # Preserve existing update notes and add new one
        existing_notes = [n.model_dump() for n in existing.content.update_notes]
        new_note = UpdateNote(date=today, note="Updated")
        all_notes = existing_notes + [new_note.model_dump()]

        # Merge update notes from input if any
        if update_notes:
            all_notes = [n.model_dump() for n in update_notes]

        atom_content = AtomContent(
            summary=content.get("summary", existing.content.summary),
            details=content.get("details", existing.content.details),
            pitfalls=content.get("pitfalls", existing.content.pitfalls),
            update_notes=[UpdateNote(**n) for n in all_notes],
        )

        # Build updated atom
        atom = Atom(
            id=existing.id,
            title=title,
            type=AtomType(type),
            status=AtomStatus(status),
            confidence=Confidence(confidence),
            content=atom_content,
            language=language,
            created_at=existing.created_at,
            updated_at=today,
            tags=tags or [],
            sources=[Source(**s) for s in (sources or [])],
            links=[Link(**ln) for ln in (links or [])],
            supersedes=existing.supersedes,
            superseded_by=existing.superseded_by,
        )

        # Save atom and update index
        self._atom_storage.save(atom)
        entry = IndexEntry.from_atom(atom)
        self._index_manager.add_or_update(entry)

        return atom.model_dump()
