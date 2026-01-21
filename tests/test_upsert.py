"""Tests for upsert tool."""

import pytest

from knowledge_mcp.tools.upsert import UpsertHandler
from knowledge_mcp.storage.atoms import AtomStorage
from knowledge_mcp.storage.index import IndexManager


class TestUpsertHandler:
    """Tests for UpsertHandler class."""

    def test_create_new_atom(self, config, sample_atom_data):
        """Test creating a new atom."""
        handler = UpsertHandler(config)
        result = handler.upsert(**sample_atom_data)

        assert result["id"] == "K-000001"
        assert result["title"] == "Test Pattern"
        assert result["type"] == "pattern"
        assert result["status"] == "active"
        assert result["confidence"] == "high"
        assert result["content"]["summary"] == "A test pattern for unit testing."
        assert result["language"] == "python"
        assert "test" in result["tags"]

    def test_create_with_explicit_id(self, config, sample_atom_data):
        """Test creating an atom with explicit ID."""
        handler = UpsertHandler(config)
        sample_atom_data["id"] = "K-000042"
        result = handler.upsert(**sample_atom_data)

        assert result["id"] == "K-000042"

    def test_update_existing_atom(self, config, sample_atom_data):
        """Test updating an existing atom."""
        handler = UpsertHandler(config)

        # Create initial atom
        result1 = handler.upsert(**sample_atom_data)
        atom_id = result1["id"]

        # Update it
        sample_atom_data["id"] = atom_id
        sample_atom_data["title"] = "Updated Pattern"
        sample_atom_data["content"]["summary"] = "Updated summary"
        result2 = handler.upsert(**sample_atom_data)

        assert result2["id"] == atom_id
        assert result2["title"] == "Updated Pattern"
        assert result2["content"]["summary"] == "Updated summary"
        # Original created_at should be preserved
        assert result2["created_at"] == result1["created_at"]

    def test_atom_saved_to_storage(self, config, sample_atom_data):
        """Test that atom is saved to storage."""
        handler = UpsertHandler(config)
        storage = AtomStorage(config)

        result = handler.upsert(**sample_atom_data)
        atom_id = result["id"]

        # Verify atom exists in storage
        loaded = storage.load(atom_id)
        assert loaded is not None
        assert loaded.title == "Test Pattern"

    def test_index_updated(self, config, sample_atom_data):
        """Test that index is updated after upsert."""
        handler = UpsertHandler(config)
        index_manager = IndexManager(config)

        result = handler.upsert(**sample_atom_data)
        atom_id = result["id"]

        # Reload index and verify
        index_manager.invalidate_cache()
        entry = index_manager.find_by_id(atom_id)
        assert entry is not None
        assert entry.title == "Test Pattern"
        assert entry.type.value == "pattern"

    def test_create_multiple_atoms(self, config, sample_atom_data):
        """Test creating multiple atoms gets sequential IDs."""
        handler = UpsertHandler(config)

        result1 = handler.upsert(**sample_atom_data)
        assert result1["id"] == "K-000001"

        sample_atom_data["title"] = "Another Pattern"
        result2 = handler.upsert(**sample_atom_data)
        assert result2["id"] == "K-000002"

        sample_atom_data["title"] = "Third Pattern"
        result3 = handler.upsert(**sample_atom_data)
        assert result3["id"] == "K-000003"

    def test_upsert_with_sources_and_links(self, config, sample_atom_data):
        """Test creating atom with sources and links."""
        handler = UpsertHandler(config)

        sample_atom_data["sources"] = [
            {"kind": "repo_path", "ref": "src/utils/test.py"},
            {"kind": "url", "ref": "https://example.com"},
        ]
        sample_atom_data["links"] = [
            {"rel": "see_also", "id": "K-000010"},
        ]

        result = handler.upsert(**sample_atom_data)

        assert len(result["sources"]) == 2
        assert result["sources"][0]["kind"] == "repo_path"
        assert len(result["links"]) == 1
        assert result["links"][0]["rel"] == "see_also"
