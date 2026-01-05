"""
Pytest configuration and shared fixtures
"""

import pytest
import subprocess
import tempfile
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.embedding_manager import EmbeddingManager
from src.seekdb_manager import SeekDBManager


def is_docker_running() -> bool:
    """Check if Docker is running"""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_seekdb_container_running() -> bool:
    """Check if seekdb container is running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=seekdb", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "seekdb" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Skip seekdb tests if Docker or container is not available
SKIP_SEEKDB = not is_docker_running() or not is_seekdb_container_running()


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


@pytest.fixture(scope="module")
def seekdb_manager():
    """Create a SeekDBManager instance using server mode (Docker)"""
    if SKIP_SEEKDB:
        pytest.skip("SeekDB tests require Docker with seekdb container running. "
                   "Start with: docker-compose up -d")

    # Use server mode connecting to Docker container
    manager = SeekDBManager(
        mode="server",
        host=config.seekdb.seekdb_host,
        port=config.seekdb.seekdb_port,
        user=config.seekdb.seekdb_user,
        password=config.seekdb.seekdb_password,
        database=config.seekdb.seekdb_database
    )

    # Initialize collections for testing
    try:
        manager.initialize_collections(embedding_dims=config.seekdb.embedding_dims)
    except Exception:
        # Collections might already exist, that's OK
        pass

    yield manager

    # Cleanup: Delete test data (optional)
    # Note: In a real scenario, you might want to clean up test documents
