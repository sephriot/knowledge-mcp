"""Tests for search tool."""

import pytest

from knowledge_mcp.tools.search import SearchEngine
from knowledge_mcp.tools.upsert import UpsertHandler


class TestSearchEngine:
    """Tests for SearchEngine class."""

    @pytest.fixture
    def populated_knowledge(self, config):
        """Populate knowledge with test atoms."""
        handler = UpsertHandler(config)

        # Create various atoms for testing
        atoms = [
            {
                "title": "Error Handling Pattern",
                "type": "pattern",
                "status": "active",
                "confidence": "high",
                "content": {
                    "summary": "Centralized error handling using Result types.",
                    "details": "Always wrap async operations in try-catch.",
                },
                "language": "typescript",
                "tags": ["error-handling", "async", "best-practice"],
            },
            {
                "title": "Database Connection Decision",
                "type": "decision",
                "status": "active",
                "confidence": "medium",
                "content": {
                    "summary": "Using PostgreSQL for main database.",
                    "details": "Selected PostgreSQL for ACID compliance.",
                },
                "language": "sql",
                "tags": ["database", "infrastructure"],
            },
            {
                "title": "API Rate Limiting",
                "type": "gotcha",
                "status": "active",
                "confidence": "high",
                "content": {
                    "summary": "External API has 100 req/min limit.",
                    "details": "Implement exponential backoff.",
                },
                "language": "python",
                "tags": ["api", "rate-limit"],
            },
            {
                "title": "Old Authentication Method",
                "type": "pattern",
                "status": "deprecated",
                "confidence": "low",
                "content": {
                    "summary": "Deprecated JWT handling.",
                    "details": "Use new OAuth2 flow instead.",
                },
                "language": "typescript",
                "tags": ["auth", "deprecated"],
            },
        ]

        for atom in atoms:
            handler.upsert(**atom)

        return config

    def test_search_by_title(self, populated_knowledge):
        """Test searching by title."""
        engine = SearchEngine(populated_knowledge)
        results = engine.search("Error Handling")

        assert len(results) >= 1
        assert results[0]["title"] == "Error Handling Pattern"

    def test_search_by_tag(self, populated_knowledge):
        """Test searching by tag."""
        engine = SearchEngine(populated_knowledge)
        results = engine.search("", tags=["database"])

        assert len(results) == 1
        assert results[0]["title"] == "Database Connection Decision"

    def test_search_filter_by_type(self, populated_knowledge):
        """Test filtering by type."""
        engine = SearchEngine(populated_knowledge)
        results = engine.search("", types=["pattern"])

        assert len(results) >= 1
        for result in results:
            assert result["type"] == "pattern"

    def test_search_filter_by_language(self, populated_knowledge):
        """Test filtering by language."""
        engine = SearchEngine(populated_knowledge)
        results = engine.search("", language="typescript")

        assert len(results) >= 1
        for result in results:
            assert result["language"] == "typescript"

    def test_search_filter_by_status(self, populated_knowledge):
        """Test filtering by status."""
        engine = SearchEngine(populated_knowledge)
        results = engine.search("", status="deprecated")

        assert len(results) == 1
        assert results[0]["title"] == "Old Authentication Method"

    def test_search_limit(self, populated_knowledge):
        """Test limiting results."""
        engine = SearchEngine(populated_knowledge)
        results = engine.search("", limit=2)

        assert len(results) <= 2

    def test_search_ranking_active_over_deprecated(self, populated_knowledge):
        """Test that active atoms rank higher than deprecated."""
        engine = SearchEngine(populated_knowledge)
        # Search for something that matches both active and deprecated
        results = engine.search("Pattern")

        # Active should come before deprecated
        active_indices = [
            i for i, r in enumerate(results) if r["status"] == "active"
        ]
        deprecated_indices = [
            i for i, r in enumerate(results) if r["status"] == "deprecated"
        ]

        if active_indices and deprecated_indices:
            assert min(active_indices) < min(deprecated_indices)

    def test_search_returns_summary(self, populated_knowledge):
        """Test that search results include summary."""
        engine = SearchEngine(populated_knowledge)
        results = engine.search("Error")

        assert len(results) >= 1
        assert "summary" in results[0]
        assert "Result types" in results[0]["summary"]

    def test_search_content(self, populated_knowledge):
        """Test deep content search."""
        engine = SearchEngine(populated_knowledge)
        # Search for something in the details
        results = engine.search_content("exponential backoff")

        assert len(results) >= 1
        assert results[0]["title"] == "API Rate Limiting"

    def test_search_empty_query_returns_all(self, populated_knowledge):
        """Test that empty query returns all atoms."""
        engine = SearchEngine(populated_knowledge)
        results = engine.search("", limit=100)

        # Should return all 4 atoms
        assert len(results) == 4

    def test_search_no_results(self, populated_knowledge):
        """Test search with no matches."""
        engine = SearchEngine(populated_knowledge)
        results = engine.search("xyznonexistent")

        assert len(results) == 0

    def test_search_case_insensitive(self, populated_knowledge):
        """Test that search is case insensitive."""
        engine = SearchEngine(populated_knowledge)

        results_lower = engine.search("error handling")
        results_upper = engine.search("ERROR HANDLING")

        assert len(results_lower) == len(results_upper)
        if results_lower:
            assert results_lower[0]["id"] == results_upper[0]["id"]
