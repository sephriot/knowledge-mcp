"""Tests for storage layer."""

import pytest

from knowledge_mcp.models.atom import Atom, AtomContent, AtomType, AtomStatus, Confidence
from knowledge_mcp.storage.atoms import AtomStorage
from knowledge_mcp.storage.index import IndexManager


class TestAtomStorage:
    """Tests for AtomStorage class."""

    def test_save_and_load_atom(self, config):
        """Test saving and loading an atom."""
        storage = AtomStorage(config)

        atom = Atom(
            id="K-000001",
            title="Test Atom",
            type=AtomType.FACT,
            status=AtomStatus.ACTIVE,
            confidence=Confidence.HIGH,
            content=AtomContent(
                summary="Test summary",
                details="Test details",
            ),
            created_at="2025-01-21",
            updated_at="2025-01-21",
            tags=["test"],
        )

        storage.save(atom)
        loaded = storage.load("K-000001")

        assert loaded is not None
        assert loaded.id == "K-000001"
        assert loaded.title == "Test Atom"
        assert loaded.type == AtomType.FACT
        assert loaded.content.summary == "Test summary"

    def test_load_nonexistent_atom(self, config):
        """Test loading an atom that doesn't exist."""
        storage = AtomStorage(config)
        loaded = storage.load("K-999999")
        assert loaded is None

    def test_exists(self, config):
        """Test checking if atom exists."""
        storage = AtomStorage(config)

        assert not storage.exists("K-000001")

        atom = Atom(
            id="K-000001",
            title="Test",
            type=AtomType.FACT,
            status=AtomStatus.ACTIVE,
            confidence=Confidence.HIGH,
            content=AtomContent(summary="Test"),
            created_at="2025-01-21",
            updated_at="2025-01-21",
        )
        storage.save(atom)

        assert storage.exists("K-000001")

    def test_delete_atom(self, config):
        """Test deleting an atom."""
        storage = AtomStorage(config)

        atom = Atom(
            id="K-000001",
            title="Test",
            type=AtomType.FACT,
            status=AtomStatus.ACTIVE,
            confidence=Confidence.HIGH,
            content=AtomContent(summary="Test"),
            created_at="2025-01-21",
            updated_at="2025-01-21",
        )
        storage.save(atom)
        assert storage.exists("K-000001")

        storage.delete("K-000001")
        assert not storage.exists("K-000001")

    def test_list_all_ids(self, config):
        """Test listing all atom IDs."""
        storage = AtomStorage(config)

        # Initially empty
        assert storage.list_all_ids() == []

        # Add some atoms
        for i in range(3):
            atom = Atom(
                id=f"K-{i+1:06d}",
                title=f"Test {i}",
                type=AtomType.FACT,
                status=AtomStatus.ACTIVE,
                confidence=Confidence.HIGH,
                content=AtomContent(summary=f"Test {i}"),
                created_at="2025-01-21",
                updated_at="2025-01-21",
            )
            storage.save(atom)

        ids = storage.list_all_ids()
        assert len(ids) == 3
        assert "K-000001" in ids
        assert "K-000002" in ids
        assert "K-000003" in ids


class TestIndexManager:
    """Tests for IndexManager class."""

    def test_load_creates_empty_index(self, config):
        """Test that loading creates an empty index if none exists."""
        manager = IndexManager(config)
        index = manager.load()

        assert index.version == 1
        assert index.atoms == []

    def test_get_next_id_empty(self, config):
        """Test getting next ID with empty index."""
        manager = IndexManager(config)
        next_id = manager.get_next_id()
        assert next_id == "K-000001"

    def test_get_next_id_with_atoms(self, config):
        """Test getting next ID with existing atoms."""
        from knowledge_mcp.models.atom import IndexEntry

        manager = IndexManager(config)
        index = manager.get_index()

        # Add some entries
        index.add_or_update(IndexEntry(
            id="K-000001",
            title="Test 1",
            type=AtomType.FACT,
            status=AtomStatus.ACTIVE,
            confidence=Confidence.HIGH,
            tags=[],
            path="atoms/K-000001.json",
            updated_at="2025-01-21",
        ))
        index.add_or_update(IndexEntry(
            id="K-000005",
            title="Test 5",
            type=AtomType.FACT,
            status=AtomStatus.ACTIVE,
            confidence=Confidence.HIGH,
            tags=[],
            path="atoms/K-000005.json",
            updated_at="2025-01-21",
        ))
        manager.save()

        next_id = manager.get_next_id()
        assert next_id == "K-000006"

    def test_find_by_id(self, config):
        """Test finding an entry by ID."""
        from knowledge_mcp.models.atom import IndexEntry

        manager = IndexManager(config)
        index = manager.get_index()

        entry = IndexEntry(
            id="K-000001",
            title="Test",
            type=AtomType.FACT,
            status=AtomStatus.ACTIVE,
            confidence=Confidence.HIGH,
            tags=["test"],
            path="atoms/K-000001.json",
            updated_at="2025-01-21",
        )
        index.add_or_update(entry)
        manager.save()

        found = manager.find_by_id("K-000001")
        assert found is not None
        assert found.title == "Test"

        not_found = manager.find_by_id("K-999999")
        assert not_found is None

    def test_remove_entry(self, config):
        """Test removing an entry from the index."""
        from knowledge_mcp.models.atom import IndexEntry

        manager = IndexManager(config)
        index = manager.get_index()

        entry = IndexEntry(
            id="K-000001",
            title="Test",
            type=AtomType.FACT,
            status=AtomStatus.ACTIVE,
            confidence=Confidence.HIGH,
            tags=[],
            path="atoms/K-000001.json",
            updated_at="2025-01-21",
        )
        index.add_or_update(entry)
        manager.save()

        assert manager.find_by_id("K-000001") is not None

        result = manager.remove("K-000001")
        assert result is True
        assert manager.find_by_id("K-000001") is None

        result = manager.remove("K-999999")
        assert result is False
