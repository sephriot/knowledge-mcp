"""Upsert handler for knowledge atoms."""

from __future__ import annotations

from datetime import date
from typing import Any

from ..config import Config, get_config
from ..models.atom import Atom, AtomContent, Link, Source, UpdateNote
from ..models.enums import AtomStatus, AtomType, Confidence, LinkRel, SourceKind
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


class UpsertHandler:
    """Handles upsert operations."""

    def __init__(
        self,
        config: Config | None = None,
        index_manager: IndexManager | None = None,
        atom_storage: AtomStorage | None = None,
    ) -> None:
        self.config = config or get_config()
        self.index_manager = index_manager or IndexManager(self.config)
        self.atom_storage = atom_storage or AtomStorage(self.config)

    def upsert(
        self,
        title: str,
        type: str,
        status: str,
        confidence: str,
        summary: str,
        details: str | None = None,
        pitfalls: list[str] | None = None,
        id: str | None = None,
        language: str | None = None,
        tags: list[str] | None = None,
        sources: list[dict[str, str]] | None = None,
        links: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Create or update a knowledge atom.

        Args:
            title: Short descriptive title
            type: Atom type (fact, decision, procedure, pattern, gotcha, glossary, snippet)
            status: Status (active, draft, deprecated)
            confidence: Confidence level (high, medium, low)
            summary: Main content summary
            details: Detailed explanation
            pitfalls: List of potential pitfalls
            id: Optional ID for updates (auto-generated for new atoms)
            language: Programming language
            tags: Keywords for search
            sources: Reference sources [{"kind": "repo_path", "ref": "src/file.ts"}]
            links: Related atoms [{"rel": "see_also", "id": "K-000001"}]

        Returns:
            The created/updated atom as dict
        """
        # Validate enum fields
        try:
            atom_type = AtomType(type)
        except ValueError:
            raise ValueError(f"Invalid atom type: {type}")

        try:
            atom_status = AtomStatus(status)
        except ValueError:
            raise ValueError(f"Invalid atom status: {status}")

        try:
            atom_confidence = Confidence(confidence)
        except ValueError:
            raise ValueError(f"Invalid confidence level: {confidence}")

        today = date.today().isoformat()

        # Handle existing atom update
        if id:
            existing = self.atom_storage.load(id)
            if existing is not None:
                return self._update_atom(
                    existing,
                    title=title,
                    atom_type=atom_type,
                    atom_status=atom_status,
                    atom_confidence=atom_confidence,
                    summary=summary,
                    details=details,
                    pitfalls=pitfalls,
                    language=language,
                    tags=tags,
                    sources=sources,
                    links=links,
                    today=today,
                )

        # Create new atom
        atom_id = id if id else self.index_manager.get_next_id()

        # Parse sources and links
        parsed_sources = self._parse_sources(sources)
        parsed_links = self._parse_links(links)

        # Build content
        atom_content = AtomContent(
            summary=summary,
            details=details or "",
            pitfalls=pitfalls or [],
            update_notes=[UpdateNote(date=today, note="Initial creation")],
        )

        # Build atom
        atom = Atom(
            id=atom_id,
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
            supersedes=[],
        )

        # Save atom and update index
        self.atom_storage.save(atom)
        entry = IndexEntry.from_atom(atom)
        self.index_manager.add_or_update(entry)

        return _atom_to_map(atom)

    def _update_atom(
        self,
        existing: Atom,
        title: str,
        atom_type: AtomType,
        atom_status: AtomStatus,
        atom_confidence: Confidence,
        summary: str,
        details: str | None,
        pitfalls: list[str] | None,
        language: str | None,
        tags: list[str] | None,
        sources: list[dict[str, str]] | None,
        links: list[dict[str, str]] | None,
        today: str,
    ) -> dict[str, Any]:
        """Update an existing atom."""
        # Preserve existing update notes and add new one
        update_notes = list(existing.content.update_notes)
        update_notes.append(UpdateNote(date=today, note="Updated"))

        # Preserve existing values if input is None
        final_pitfalls = pitfalls if pitfalls is not None else existing.content.pitfalls
        final_tags = tags if tags is not None else existing.tags
        final_sources = self._parse_sources(sources) if sources is not None else existing.sources
        final_links = self._parse_links(links) if links is not None else existing.links
        final_details = details if details else existing.content.details

        # Build content
        atom_content = AtomContent(
            summary=summary,
            details=final_details,
            pitfalls=final_pitfalls,
            update_notes=update_notes,
        )

        # Build updated atom
        atom = Atom(
            id=existing.id,
            title=title,
            type=atom_type,
            status=atom_status,
            confidence=atom_confidence,
            content=atom_content,
            language=language,
            created_at=existing.created_at,
            updated_at=today,
            tags=final_tags,
            sources=final_sources,
            links=final_links,
            supersedes=existing.supersedes,
            superseded_by=existing.superseded_by,
        )

        # Save atom and update index
        self.atom_storage.save(atom)
        entry = IndexEntry.from_atom(atom)
        self.index_manager.add_or_update(entry)

        return _atom_to_map(atom)

    def _parse_sources(self, sources: list[dict[str, str]] | None) -> list[Source]:
        """Parse source dicts into Source objects."""
        if not sources:
            return []
        result = []
        for s in sources:
            try:
                kind = SourceKind(s.get("kind", ""))
                ref = s.get("ref", "")
                result.append(Source(kind=kind, ref=ref))
            except ValueError:
                pass  # Skip invalid sources
        return result

    def _parse_links(self, links: list[dict[str, str]] | None) -> list[Link]:
        """Parse link dicts into Link objects."""
        if not links:
            return []
        result = []
        for l in links:
            try:
                rel = LinkRel(l.get("rel", ""))
                link_id = l.get("id", "")
                result.append(Link(rel=rel, id=link_id))
            except ValueError:
                pass  # Skip invalid links
        return result
