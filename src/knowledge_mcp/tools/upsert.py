"""Upsert tool implementation."""

from datetime import date

from ..config import Config, get_config
from ..models.atom import (
    Atom,
    AtomContent,
    AtomContentInput,
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
        type: AtomType | str,
        status: AtomStatus | str,
        confidence: Confidence | str,
        content: AtomContentInput | dict,
        id: str | None = None,
        language: str | None = None,
        tags: list[str] | None = None,
        sources: list[Source] | list[dict] | None = None,
        links: list[Link] | list[dict] | None = None,
    ) -> dict:
        """Create or update a knowledge atom.

        Args:
            title: Short descriptive title.
            type: Atom type.
            status: Status.
            confidence: Confidence level.
            content: Content input object.
            id: Optional ID for updates. If not provided, creates a new atom.
            language: Optional programming language.
            tags: Optional list of tags.
            sources: Optional list of source references.
            links: Optional list of links to other atoms.

        Returns:
            The created/updated atom as a dictionary.
        """
        today = date.today().isoformat()

        # Normalize inputs (handle Pydantic models or dicts/strings)
        # This ensures backward compatibility if called internally with dicts
        atom_type = AtomType(type) if isinstance(type, str) else type
        atom_status = AtomStatus(status) if isinstance(status, str) else status
        atom_confidence = Confidence(confidence) if isinstance(confidence, str) else confidence
        
        # Parse content if it's a dict (internal use)
        if isinstance(content, dict):
            # Map dict to AtomContentInput logic manually or just use as is
            # For simplicity, we'll convert strictly in the logic below
            pass
        
        # Parse sources/links if they are dicts
        parsed_sources = []
        if sources:
            for s in sources:
                if isinstance(s, dict):
                    parsed_sources.append(Source(**s))
                else:
                    parsed_sources.append(s)
                    
        parsed_links = []
        if links:
            for l in links:
                if isinstance(l, dict):
                    parsed_links.append(Link(**l))
                else:
                    parsed_links.append(l)

        # Handle existing atom update
        if id:
            existing = self._atom_storage.load(id)
            if existing:
                return self._update_atom(
                    existing,
                    title=title,
                    type=atom_type,
                    status=atom_status,
                    confidence=atom_confidence,
                    content=content,
                    language=language,
                    tags=tags,
                    sources=parsed_sources,
                    links=parsed_links,
                )

        # Create new atom
        if id is None:
            id = self._index_manager.get_next_id()

        # Build content object
        # Handle both AtomContentInput object and dict (legacy/internal)
        summary = content.summary if isinstance(content, AtomContentInput) else content.get("summary", "")
        details = (content.details if isinstance(content, AtomContentInput) else content.get("details")) or ""
        pitfalls = (content.pitfalls if isinstance(content, AtomContentInput) else content.get("pitfalls")) or []
        
        input_notes = (content.update_notes if isinstance(content, AtomContentInput) else content.get("update_notes")) or []
        update_notes = []
        for note in input_notes:
            if isinstance(note, UpdateNote):
                update_notes.append(note)
            elif isinstance(note, dict):
                update_notes.append(UpdateNote(**note))

        atom_content = AtomContent(
            summary=summary,
            details=details,
            pitfalls=pitfalls,
            update_notes=update_notes,
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
            type=atom_type,
            status=atom_status,
            confidence=atom_confidence,
            content=atom_content,
            language=language,
            created_at=today,
            updated_at=today,
            tags=tags or [],
            sources=parsed_sources,
            links=parsed_links,
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
        type: AtomType,
        status: AtomStatus,
        confidence: Confidence,
        content: AtomContentInput | dict,
        language: str | None = None,
        tags: list[str] | None = None,
        sources: list[Source] | None = None,
        links: list[Link] | None = None,
    ) -> dict:
        """Update an existing atom."""
        today = date.today().isoformat()

        # Build content object
        input_notes = (content.update_notes if isinstance(content, AtomContentInput) else content.get("update_notes")) or []
        update_notes = []
        for note in input_notes:
            if isinstance(note, UpdateNote):
                update_notes.append(note)
            elif isinstance(note, dict):
                update_notes.append(UpdateNote(**note))

        # Preserve existing update notes and add new one
        existing_notes = [n.model_dump() for n in existing.content.update_notes]
        new_note = UpdateNote(date=today, note="Updated")
        all_notes = existing_notes + [new_note.model_dump()]

        # Merge update notes from input if any (replace behavior if provided?)
        # Original logic: if update_notes provided, use them. Else append "Updated".
        # But wait, original logic:
        # if update_notes: all_notes = [n.model_dump() for n in update_notes]
        if update_notes:
             all_notes = [n.model_dump() for n in update_notes]
        else:
             # Use existing + new note
             # (already set above)
             pass

        # Handle content fields merge
        if isinstance(content, AtomContentInput):
            summary = content.summary  # Required in input, so always present
            # For details/pitfalls, we use existing if input is None (partial update)
            details = content.details if content.details is not None else existing.content.details
            pitfalls = content.pitfalls if content.pitfalls is not None else existing.content.pitfalls
        else:
            summary = content.get("summary", existing.content.summary)
            details = content.get("details", existing.content.details)
            pitfalls = content.get("pitfalls", existing.content.pitfalls)

        atom_content = AtomContent(
            summary=summary,
            details=details,
            pitfalls=pitfalls,
            update_notes=[UpdateNote(**n) for n in all_notes],
        )

        # Build updated atom
        atom = Atom(
            id=existing.id,
            title=title,
            type=type,
            status=status,
            confidence=confidence,
            content=atom_content,
            language=language,
            created_at=existing.created_at,
            updated_at=today,
            tags=tags or [],
            sources=sources or [],
            links=links or [],
            supersedes=existing.supersedes,
            superseded_by=existing.superseded_by,
        )

        # Save atom and update index
        self._atom_storage.save(atom)
        entry = IndexEntry.from_atom(atom)
        self._index_manager.add_or_update(entry)

        return atom.model_dump()
