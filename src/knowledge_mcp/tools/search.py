"""Search tool implementation."""

from ..config import Config, get_config
from ..models.atom import AtomStatus, AtomType, Confidence, IndexEntry
from ..storage.atoms import AtomStorage
from ..storage.index import IndexManager


class SearchEngine:
    """Search engine for knowledge atoms."""

    # Priority values for ranking
    STATUS_PRIORITY = {
        AtomStatus.ACTIVE: 3,
        AtomStatus.DRAFT: 2,
        AtomStatus.DEPRECATED: 1,
    }

    CONFIDENCE_PRIORITY = {
        Confidence.HIGH: 3,
        Confidence.MEDIUM: 2,
        Confidence.LOW: 1,
    }

    def __init__(self, config: Config | None = None):
        """Initialize the search engine.

        Args:
            config: Configuration instance. Uses global config if not provided.
        """
        self._config = config or get_config()
        self._index_manager = IndexManager(self._config)
        self._atom_storage = AtomStorage(self._config)

    def search(
        self,
        query: str,
        types: list[str] | None = None,
        tags: list[str] | None = None,
        language: str | None = None,
        status: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search for knowledge atoms.

        Args:
            query: Search query string.
            types: Filter by atom types.
            tags: Filter by tags.
            language: Filter by programming language.
            status: Filter by status.
            limit: Maximum number of results.

        Returns:
            List of search results with metadata and content summary.
        """
        index = self._index_manager.get_index()
        results: list[tuple[IndexEntry, int]] = []

        # Convert types to enum values
        type_enums: set[AtomType] | None = None
        if types:
            type_enums = {AtomType(t) for t in types}

        # Convert status to enum
        status_enum: AtomStatus | None = None
        if status:
            status_enum = AtomStatus(status)

        query_lower = query.lower()

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

            # Calculate relevance score
            score = self._calculate_score(entry, query_lower)
            if score > 0:
                results.append((entry, score))

        # Sort by score (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        # Limit results
        results = results[:limit]

        # Format results with content summary
        return [self._format_result(entry, score) for entry, score in results]

    def _calculate_score(self, entry: IndexEntry, query_lower: str) -> int:
        """Calculate relevance score for an entry.

        Args:
            entry: The index entry to score.
            query_lower: Lowercase search query.

        Returns:
            Relevance score (0 = no match, unless query is empty).
        """
        # Empty query returns all atoms with base score
        if not query_lower:
            base_score = 10
            base_score += self.STATUS_PRIORITY.get(entry.status, 0) * 5
            base_score += self.CONFIDENCE_PRIORITY.get(entry.confidence, 0) * 3
            return base_score

        # Non-empty query: must match in title or tags
        match_score = 0

        # Title match (highest weight)
        title_lower = entry.title.lower()
        if query_lower in title_lower:
            match_score += 100
            if title_lower.startswith(query_lower):
                match_score += 50

        # Tag match
        for tag in entry.tags:
            if query_lower in tag.lower():
                match_score += 30

        # No match found - return 0
        if match_score == 0:
            return 0

        # Add status and confidence priority for matched entries
        match_score += self.STATUS_PRIORITY.get(entry.status, 0) * 5
        match_score += self.CONFIDENCE_PRIORITY.get(entry.confidence, 0) * 3

        return match_score

    def _format_result(self, entry: IndexEntry, score: int) -> dict:
        """Format a search result.

        Args:
            entry: The index entry.
            score: The relevance score.

        Returns:
            Formatted result dictionary.
        """
        result = {
            "id": entry.id,
            "title": entry.title,
            "type": entry.type.value,
            "status": entry.status.value,
            "confidence": entry.confidence.value,
            "language": entry.language,
            "tags": entry.tags,
            "updated_at": entry.updated_at,
            "score": score,
        }

        # Load atom to get content summary
        atom = self._atom_storage.load(entry.id)
        if atom:
            result["summary"] = atom.content.summary

        return result

    def search_content(
        self,
        query: str,
        types: list[str] | None = None,
        tags: list[str] | None = None,
        language: str | None = None,
        status: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Deep search including atom content.

        Args:
            query: Search query string.
            types: Filter by atom types.
            tags: Filter by tags.
            language: Filter by programming language.
            status: Filter by status.
            limit: Maximum number of results.

        Returns:
            List of search results with metadata and content summary.
        """
        index = self._index_manager.get_index()
        results: list[tuple[IndexEntry, int]] = []

        # Convert types to enum values
        type_enums: set[AtomType] | None = None
        if types:
            type_enums = {AtomType(t) for t in types}

        # Convert status to enum
        status_enum: AtomStatus | None = None
        if status:
            status_enum = AtomStatus(status)

        query_lower = query.lower()

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

            # Calculate relevance score (including content)
            score = self._calculate_content_score(entry, query_lower)
            if score > 0:
                results.append((entry, score))

        # Sort by score (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        # Limit results
        results = results[:limit]

        # Format results with content summary
        return [self._format_result(entry, score) for entry, score in results]

    def _calculate_content_score(self, entry: IndexEntry, query_lower: str) -> int:
        """Calculate relevance score including content search.

        Args:
            entry: The index entry to score.
            query_lower: Lowercase search query.

        Returns:
            Relevance score (0 = no match, unless query is empty).
        """
        # Empty query returns all atoms with base score
        if not query_lower:
            base_score = 10
            base_score += self.STATUS_PRIORITY.get(entry.status, 0) * 5
            base_score += self.CONFIDENCE_PRIORITY.get(entry.confidence, 0) * 3
            return base_score

        # Start with basic score from title/tag matching
        score = self._calculate_score(entry, query_lower)

        # Also search in content
        atom = self._atom_storage.load(entry.id)
        if atom:
            content_text = (
                atom.content.summary.lower()
                + " "
                + atom.content.details.lower()
            )
            if query_lower in content_text:
                # If no title/tag match, give a base content match score
                if score == 0:
                    score = 20
                    score += self.STATUS_PRIORITY.get(entry.status, 0) * 5
                    score += self.CONFIDENCE_PRIORITY.get(entry.confidence, 0) * 3
                else:
                    score += 20

        return score
