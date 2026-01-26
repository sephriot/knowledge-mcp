"""Search engine for knowledge atoms."""

from __future__ import annotations

import math
from typing import Any

from ..config import Config, get_config
from ..models.enums import AtomStatus, AtomType, Confidence
from ..models.index import IndexEntry
from ..storage.atoms import AtomStorage
from ..storage.index import IndexManager

# Priority values for ranking
STATUS_PRIORITY: dict[str, int] = {
    AtomStatus.ACTIVE.value: 3,
    AtomStatus.DRAFT.value: 2,
    AtomStatus.DEPRECATED.value: 1,
}

CONFIDENCE_PRIORITY: dict[str, int] = {
    Confidence.HIGH.value: 3,
    Confidence.MEDIUM.value: 2,
    Confidence.LOW.value: 1,
}


def _popularity_score(popularity: int) -> int:
    """Calculate popularity bonus (logarithmic, max 25 points).

    Uses log2 scaling to provide diminishing returns:
    - popularity=0  ->  0 pts
    - popularity=1  ->  5 pts
    - popularity=3  -> 10 pts
    - popularity=7  -> 15 pts
    - popularity=15 -> 20 pts
    - popularity=31 -> 25 pts (capped)
    """
    if popularity <= 0:
        return 0
    return min(25, int(5 * math.log2(popularity + 1)))


class SearchEngine:
    """Handles search operations."""

    def __init__(
        self,
        config: Config | None = None,
        index_manager: IndexManager | None = None,
        atom_storage: AtomStorage | None = None,
    ) -> None:
        self.config = config or get_config()
        self.index_manager = index_manager or IndexManager(self.config)
        self.atom_storage = atom_storage or AtomStorage(self.config)

    def search(
        self,
        query: list[str],
        types: list[str] | None,
        tags: list[str] | None,
        language: str | None,
        status: str | None,
        limit: int,
        include_content: bool = False,
    ) -> list[dict[str, Any]]:
        """Search for knowledge atoms.

        Args:
            query: Search tokens (OR logic with cumulative scoring)
            types: Filter by atom types
            tags: Filter by tags (case-insensitive)
            language: Filter by programming language
            status: Filter by status
            limit: Maximum results
            include_content: Also search in atom content (slower)

        Returns:
            List of search results with scores
        """
        index = self.index_manager.get_index()
        query_tokens = self._normalize_tokens(query)

        # Convert types to set for fast lookup
        type_set = set(types) if types else set()

        scored_results: list[tuple[IndexEntry, int]] = []

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

            # Calculate relevance score
            if include_content:
                score = self._calculate_content_score(entry, query_tokens)
            else:
                score = self._calculate_score(entry, query_tokens)

            if score > 0:
                scored_results.append((entry, score))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Limit results
        scored_results = scored_results[:limit]

        # Format results
        return [self._format_result(entry, score) for entry, score in scored_results]

    def _normalize_tokens(self, tokens: list[str]) -> list[str]:
        """Convert query tokens to lowercase for case-insensitive matching."""
        return [t.lower() for t in tokens if t]

    def _calculate_score(self, entry: IndexEntry, query_tokens: list[str]) -> int:
        """Calculate relevance score for an entry."""
        # Empty query returns all atoms with base score
        if not query_tokens:
            base_score = 10
            base_score += STATUS_PRIORITY.get(entry.status, 0) * 5
            base_score += CONFIDENCE_PRIORITY.get(entry.confidence, 0) * 3
            return base_score

        match_score = 0
        title_lower = entry.title.lower()

        # Check each token - OR logic with cumulative scoring
        for token in query_tokens:
            # Title match (highest weight per token)
            if token in title_lower:
                match_score += 100
                if title_lower.startswith(token):
                    match_score += 50

            # Tag match (per token)
            for tag in entry.tags:
                if token in tag.lower():
                    match_score += 30
                    break  # Only count once per token

        # No match found - return 0
        if match_score == 0:
            return 0

        # Add status and confidence priority for matched entries
        match_score += STATUS_PRIORITY.get(entry.status, 0) * 5
        match_score += CONFIDENCE_PRIORITY.get(entry.confidence, 0) * 3
        match_score += _popularity_score(entry.popularity)

        return match_score

    def _calculate_content_score(self, entry: IndexEntry, query_tokens: list[str]) -> int:
        """Calculate relevance score including content search."""
        # Empty query returns all atoms with base score
        if not query_tokens:
            base_score = 10
            base_score += STATUS_PRIORITY.get(entry.status, 0) * 5
            base_score += CONFIDENCE_PRIORITY.get(entry.confidence, 0) * 3
            return base_score

        # Start with basic score from title/tag matching
        score = self._calculate_score(entry, query_tokens)

        # Also search in content
        atom = self.atom_storage.load(entry.id)
        if atom is not None:
            content_text = (atom.content.summary + " " + atom.content.details).lower()
            for token in query_tokens:
                if token in content_text:
                    # If no title/tag match, give a base content match score
                    if score == 0:
                        score = 20
                        score += STATUS_PRIORITY.get(entry.status, 0) * 5
                        score += CONFIDENCE_PRIORITY.get(entry.confidence, 0) * 3
                        score += _popularity_score(entry.popularity)
                    else:
                        score += 20

        return score

    def _format_result(self, entry: IndexEntry, score: int) -> dict[str, Any]:
        """Format a search result."""
        result: dict[str, Any] = {
            "id": entry.id,
            "title": entry.title,
            "type": entry.type,
            "status": entry.status,
            "confidence": entry.confidence,
            "tags": entry.tags,
            "updated_at": entry.updated_at,
            "score": score,
        }

        if entry.language:
            result["language"] = entry.language

        # Load atom to get content summary
        atom = self.atom_storage.load(entry.id)
        if atom is not None:
            result["summary"] = atom.content.summary

        return result
