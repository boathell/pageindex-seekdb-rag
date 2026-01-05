"""
Pytest configuration and shared fixtures
"""

import pytest
import tempfile
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.embedding_manager import EmbeddingManager
from src.seekdb_manager import SeekDBManager


@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        "api_key": config.openai.get_api_key(),
        "model": config.openai.openai_embedding_model,
        "base_url": config.openai.base_url,
        "embedding_dims": config.seekdb.embedding_dims
    }


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_text():
    """Sample text for testing"""
    return "This is a test document about machine learning and artificial intelligence."


@pytest.fixture
def sample_texts():
    """Sample texts for batch testing"""
    return [
        "Machine learning is a subset of artificial intelligence.",
        "Deep learning uses neural networks with multiple layers.",
        "Natural language processing enables computers to understand human language.",
        "Computer vision allows machines to interpret visual information.",
        "Reinforcement learning involves learning through trial and error."
    ]


@pytest.fixture
def sample_node_data():
    """Sample node data for testing"""
    return {
        "node_id": "test_node_001",
        "parent_id": None,
        "document_id": "test_doc",
        "title": "Test Chapter",
        "summary": "This is a test chapter about testing.",
        "level": 0,
        "start_page": 1,
        "end_page": 5,
        "child_count": 0,
        "metadata": {"test": True}
    }


@pytest.fixture
def sample_chunk_data():
    """Sample chunk data for testing"""
    return {
        "chunk_id": "test_chunk_001",
        "node_id": "test_node_001",
        "document_id": "test_doc",
        "content": "This is test content for chunk testing.",
        "page_num": 1,
        "chunk_index": 0,
        "word_count": 8,
        "metadata": {"test": True}
    }


@pytest.fixture(scope="module")
def embedding_manager(test_config):
    """Create an EmbeddingManager instance for testing"""
    return EmbeddingManager(
        api_key=test_config["api_key"],
        model=test_config["model"],
        base_url=test_config["base_url"]
    )


@pytest.fixture
def seekdb_manager_embedded(temp_dir):
    """Create a SeekDBManager instance in embedded mode"""
    manager = SeekDBManager(
        mode="embedded",
        persist_directory=str(temp_dir / "test_seekdb")
    )
    yield manager
    # Cleanup is handled by temp_dir fixture
