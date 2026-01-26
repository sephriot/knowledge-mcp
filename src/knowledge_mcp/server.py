"""FastMCP server setup and tool registration."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import Config, create_config, set_config
from .storage.atoms import AtomStorage
from .storage.index import IndexManager
from .tools.atoms import AtomTools
from .tools.search import SearchEngine
from .tools.upsert import UpsertHandler

SERVER_INSTRUCTIONS = """Knowledge MCP - Project-specific knowledge management for AI agents.

## Purpose
Store and retrieve reusable knowledge to accelerate future tasks. Knowledge persists across conversations, making repeated work faster and more consistent.

## PROACTIVE KNOWLEDGE CREATION (IMPORTANT)
You are strongly encouraged to CREATE knowledge atoms proactively during your work:

- After solving a non-trivial problem -> create a "pattern" or "procedure" atom
- After discovering a gotcha or pitfall -> create a "gotcha" atom
- After making an architectural decision -> create a "decision" atom
- After learning how something works -> create a "fact" atom
- After writing reusable code -> create a "snippet" atom

This investment pays off: future tasks in this project will be faster because you'll have context ready. Don't wait to be asked - if knowledge is reusable, capture it.

## Atom Types
- fact: Verified information about the codebase, APIs, or domain
- decision: Architectural or design decisions with rationale
- procedure: Step-by-step instructions for tasks
- pattern: Reusable solutions or code patterns
- gotcha: Pitfalls, common mistakes, or non-obvious behavior
- glossary: Domain-specific terms and definitions
- snippet: Reusable code fragments

## Search Behavior
- Uses OR logic: any matching token scores points
- More matches = higher score (cumulative)
- Use include_content=true for thorough searches
- Filter by type/tags/language to narrow results

## Best Practices
1. Search BEFORE creating to avoid duplicates
2. Use descriptive titles and relevant tags
3. Keep atoms focused (one concept per atom)
4. Include sources (file paths, URLs) when applicable
5. Link related atoms using the links field
6. Mark confidence appropriately (high/medium/low)
7. Update existing atoms rather than creating duplicates"""


def create_server(
    data_path: str | None = None,
    persist_popularity: bool = False,
) -> FastMCP:
    """Create and configure the FastMCP server.

    Args:
        data_path: Path to knowledge storage directory
        persist_popularity: Whether to persist popularity counts to disk

    Returns:
        Configured FastMCP server instance
    """
    # Initialize configuration
    cfg = create_config(data_path, persist_popularity=persist_popularity)
    set_config(cfg)

    # Create server with instructions
    mcp = FastMCP(
        "knowledge-mcp",
        instructions=SERVER_INSTRUCTIONS,
    )

    # Initialize shared components
    index_manager = IndexManager(cfg)
    atom_storage = AtomStorage(cfg)
    search_engine = SearchEngine(cfg, index_manager, atom_storage)
    upsert_handler = UpsertHandler(cfg, index_manager, atom_storage)
    atom_tools = AtomTools(cfg, index_manager, atom_storage)

    # Register tools
    _register_search_tool(mcp, search_engine)
    _register_upsert_tool(mcp, upsert_handler)
    _register_atom_tools(mcp, atom_tools)

    return mcp


def _register_search_tool(mcp: FastMCP, engine: SearchEngine) -> None:
    """Register the search tool."""

    @mcp.tool()
    def search(
        query: list[str] | None = None,
        types: list[str] | None = None,
        tags: list[str] | None = None,
        language: str | None = None,
        status: str | None = None,
        limit: int = 10,
        include_content: bool = False,
    ) -> list[dict[str, Any]]:
        """Search knowledge atoms by title, tags, and content.

        Args:
            query: Search query tokens. Results match if ANY token is found (OR logic). More matches = higher score.
            types: Filter by types (fact, decision, procedure, pattern, gotcha, glossary, snippet).
            tags: Filter by tags.
            language: Filter by programming language.
            status: Filter by status (active, draft, deprecated).
            limit: Maximum results (default 10).
            include_content: Search in atom content (summary, details) too. Slower but more thorough.

        Returns:
            List of matching atoms with metadata and summary.
        """
        return engine.search(
            query=query or [],
            types=types,
            tags=tags,
            language=language,
            status=status,
            limit=limit,
            include_content=include_content,
        )


def _register_upsert_tool(mcp: FastMCP, handler: UpsertHandler) -> None:
    """Register the upsert tool."""

    @mcp.tool()
    def upsert(
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
            title: Short descriptive title.
            type: Atom type (fact, decision, procedure, pattern, gotcha, glossary, snippet).
            status: Status (active, draft, deprecated).
            confidence: Confidence level (high, medium, low).
            summary: The main content summary of the atom.
            details: Detailed explanation or code.
            pitfalls: List of potential pitfalls or things to avoid.
            id: Optional ID for updates. Auto-generated for new atoms.
            language: Programming language (optional).
            tags: Keywords for search (optional).
            sources: References like [{"kind": "repo_path", "ref": "src/file.ts"}] (optional).
            links: Related atoms like [{"rel": "see_also", "id": "K-000001"}] (optional).

        Returns:
            The created/updated atom.
        """
        return handler.upsert(
            id=id,
            title=title,
            type=type,
            status=status,
            confidence=confidence,
            summary=summary,
            details=details,
            pitfalls=pitfalls,
            language=language,
            tags=tags,
            sources=sources,
            links=links,
        )


def _register_atom_tools(mcp: FastMCP, tools: AtomTools) -> None:
    """Register atom management tools."""

    @mcp.tool()
    def get_atom(id: str) -> dict[str, Any] | None:
        """Get full atom content by ID.

        Args:
            id: The atom ID (e.g., K-000001).

        Returns:
            Full atom content or None if not found.
        """
        return tools.get_atom(id)

    @mcp.tool()
    def list_atoms(
        types: list[str] | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
        language: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List knowledge atoms with filtering.

        Args:
            types: Filter by types.
            tags: Filter by tags.
            status: Filter by status.
            language: Filter by language.
            limit: Maximum results (default 50).

        Returns:
            List of atom summaries.
        """
        return tools.list_atoms(types, tags, status, language, limit)

    @mcp.tool()
    def delete_atom(id: str) -> dict[str, Any]:
        """Deprecate an atom (sets status to deprecated).

        Args:
            id: The atom ID to deprecate.

        Returns:
            Result with success status.
        """
        return tools.delete_atom(id)

    @mcp.tool()
    def purge_atom(id: str) -> dict[str, Any]:
        """Permanently delete an atom from storage.

        WARNING: This cannot be undone. Use delete_atom to deprecate instead.

        Args:
            id: The atom ID to permanently delete.

        Returns:
            Result with success status.
        """
        return tools.purge_atom(id)

    @mcp.tool()
    def list_all_ids() -> dict[str, Any]:
        """List all atom IDs in storage.

        Returns:
            Dictionary with list of IDs and count.
        """
        return tools.list_all_ids()

    @mcp.tool()
    def get_next_id() -> dict[str, Any]:
        """Get the next available atom ID.

        Returns:
            Dictionary with next_id field (e.g., K-000001).
        """
        return tools.get_next_id()

    @mcp.tool()
    def export_all(format: str = "json") -> dict[str, Any]:
        """Export all knowledge as a single JSON structure.

        Args:
            format: Export format (only "json" supported).

        Returns:
            All atoms in a single structure.
        """
        return tools.export_all(format)

    @mcp.tool()
    def rebuild_index() -> dict[str, Any]:
        """Rebuild index.yaml from atom files.

        Use this if the index gets out of sync with the atom files.

        Returns:
            Result with count of atoms indexed.
        """
        return tools.rebuild_index()

    @mcp.tool()
    def get_summary(group_by: str = "type") -> dict[str, Any]:
        """Get summary of knowledge grouped by type, tag, or language.

        Args:
            group_by: Grouping criterion ("type", "tag", or "language").

        Returns:
            Summary with counts and items per group.
        """
        return tools.get_summary(group_by)
