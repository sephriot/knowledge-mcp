"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile
import shutil

from knowledge_mcp.config import Config, set_config


@pytest.fixture
def temp_knowledge_dir():
    """Create a temporary directory for knowledge storage."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_knowledge_dir):
    """Create a config using a temporary directory."""
    cfg = Config(data_path=temp_knowledge_dir)
    set_config(cfg)
    return cfg


@pytest.fixture
def sample_atom_data():
    """Sample atom data for testing."""
    return {
        "title": "Test Pattern",
        "type": "pattern",
        "status": "active",
        "confidence": "high",
        "content": {
            "summary": "A test pattern for unit testing.",
            "details": "This is a detailed description of the test pattern.",
            "pitfalls": ["Don't use in production"],
        },
        "language": "python",
        "tags": ["test", "example"],
    }
