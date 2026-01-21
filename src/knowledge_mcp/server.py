"""FastMCP server for knowledge management."""

import argparse
from pathlib import Path

from fastmcp import FastMCP

from .config import Config, set_config, get_config
from .tools.atoms import AtomTools
from .tools.search import SearchEngine
from .tools.upsert import UpsertHandler

# Create the MCP server
mcp = FastMCP(
    name="knowledge-mcp",
    instructions="""Knowledge MCP Server - Project-specific knowledge management.

This server provides tools to store, search, and manage knowledge atoms.
Each atom represents a piece of knowledge like a fact, decision, pattern, or gotcha.

Use 'search' to find existing knowledge, 'upsert' to create or update atoms,
and 'get_atom' to retrieve full details of a specific atom.
""",
)


# Lazy initialization of tools (will be initialized when first used)
_search_engine: SearchEngine | None = None
_upsert_handler: UpsertHandler | None = None
_atom_tools: AtomTools | None = None


def _get_search_engine() -> SearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine(get_config())
    return _search_engine


def _get_upsert_handler() -> UpsertHandler:
    global _upsert_handler
    if _upsert_handler is None:
        _upsert_handler = UpsertHandler(get_config())
    return _upsert_handler


def _get_atom_tools() -> AtomTools:
    global _atom_tools
    if _atom_tools is None:
        _atom_tools = AtomTools(get_config())
    return _atom_tools


# =============================================================================
# Core Tools
# =============================================================================


@mcp.tool
def search(
    query: str,
    types: list[str] | None = None,
    tags: list[str] | None = None,
    language: str | None = None,
    status: str | None = None,
    limit: int = 10,
    include_content: bool = False,
) -> list[dict]:
    """Search knowledge atoms by title, tags, and content.

    Args:
        query: Search query string.
        types: Filter by types (fact, decision, procedure, pattern, gotcha, glossary, snippet).
        tags: Filter by tags.
        language: Filter by programming language.
        status: Filter by status (active, draft, deprecated).
        limit: Maximum results (default 10).
        include_content: Search in atom content (summary, details) too. Slower but more thorough.

    Returns:
        List of matching atoms with metadata and summary.
    """
    engine = _get_search_engine()
    search_method = engine.search_content if include_content else engine.search
    return search_method(
        query=query,
        types=types,
        tags=tags,
        language=language,
        status=status,
        limit=limit,
    )


@mcp.tool
def upsert(
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
        content: Content with summary (required), details, pitfalls, update_notes.
        id: Optional ID for updates. Auto-generated for new atoms.
        language: Programming language (optional).
        tags: Keywords for search (optional).
        sources: References like {"kind": "repo_path", "ref": "src/file.ts"} (optional).
        links: Related atoms like {"rel": "see_also", "id": "K-000001"} (optional).

    Returns:
        The created/updated atom.
    """
    return _get_upsert_handler().upsert(
        title=title,
        type=type,
        status=status,
        confidence=confidence,
        content=content,
        id=id,
        language=language,
        tags=tags,
        sources=sources,
        links=links,
    )


# =============================================================================
# Knowledge Organization Tools
# =============================================================================


@mcp.tool
def list_atoms(
    types: list[str] | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
    language: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List knowledge atoms with filtering.

    Args:
        types: Filter by types (fact, decision, procedure, pattern, gotcha, glossary, snippet).
        tags: Filter by tags.
        status: Filter by status (active, draft, deprecated).
        language: Filter by programming language.
        limit: Maximum results (default 50).

    Returns:
        List of atom summaries.
    """
    return _get_atom_tools().list_atoms(
        types=types,
        tags=tags,
        status=status,
        language=language,
        limit=limit,
    )


@mcp.tool
def get_atom(id: str) -> dict | None:
    """Get full atom content by ID.

    Args:
        id: The atom ID (e.g., K-000001).

    Returns:
        Full atom content or None if not found.
    """
    return _get_atom_tools().get_atom(id)


@mcp.tool
def delete_atom(id: str) -> dict:
    """Deprecate an atom (sets status to deprecated).

    Args:
        id: The atom ID to deprecate.

    Returns:
        Result with success status.
    """
    return _get_atom_tools().delete_atom(id)


@mcp.tool
def purge_atom(id: str) -> dict:
    """Permanently delete an atom from storage.

    WARNING: This cannot be undone. Use delete_atom to deprecate instead.

    Args:
        id: The atom ID to permanently delete.

    Returns:
        Result with success status.
    """
    return _get_atom_tools().purge_atom(id)


@mcp.tool
def list_all_ids() -> dict:
    """List all atom IDs in storage.

    Returns:
        Dictionary with list of IDs and count.
    """
    return _get_atom_tools().list_all_ids()


# =============================================================================
# Bulk Operations
# =============================================================================


@mcp.tool
def export_all(format: str = "json") -> dict:
    """Export all knowledge as a single JSON structure.

    Args:
        format: Export format (only "json" supported).

    Returns:
        All atoms in a single structure.
    """
    return _get_atom_tools().export_all(format=format)


@mcp.tool
def rebuild_index() -> dict:
    """Rebuild index.json from atom files.

    Use this if the index gets out of sync with the atom files.

    Returns:
        Result with count of atoms indexed.
    """
    return _get_atom_tools().rebuild_index()


# =============================================================================
# Utility Tools
# =============================================================================


@mcp.tool
def get_summary(group_by: str = "type") -> dict:
    """Get summary of knowledge grouped by type, tag, or language.

    Args:
        group_by: Grouping criterion ("type", "tag", or "language").

    Returns:
        Summary with counts and items per group.
    """
    return _get_atom_tools().get_summary(group_by=group_by)


@mcp.tool
def get_next_id() -> dict:
    """Get the next available atom ID.

    Returns:
        Dictionary with next_id field (e.g., K-000001).
    """
    return _get_atom_tools().get_next_id()


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Knowledge MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Path to knowledge storage (default: .knowledge or KNOWLEDGE_MCP_PATH env)",
    )
    args = parser.parse_args()

    # Configure the data path
    if args.data_path:
        config = Config(data_path=Path(args.data_path))
        set_config(config)

    # Run the server
    mcp.run()


if __name__ == "__main__":
    main()
