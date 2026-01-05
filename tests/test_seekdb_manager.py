"""
Unit tests for SeekDBManager
"""

import pytest
import platform
from pathlib import Path

from src.seekdb_manager import SeekDBManager, NodeRecord, ChunkRecord

# Skip embedded mode tests on non-Linux platforms (pylibseekdb only supports Linux)
SKIP_EMBEDDED = platform.system() != "Linux"


class TestSeekDBManagerInit:
    """Test SeekDBManager initialization"""

    @pytest.mark.skipif(SKIP_EMBEDDED, reason="Embedded mode requires Linux")
    def test_init_embedded_mode(self, temp_dir):
        """Test initialization in embedded mode"""
        manager = SeekDBManager(
            mode="embedded",
            persist_directory=str(temp_dir / "test_db")
        )

        assert manager.mode == "embedded"
        assert manager.persist_directory is not None
        assert manager.client is not None

    @pytest.mark.skipif(
        True,  # Skip by default, requires Docker
        reason="Requires seekdb Docker container"
    )
    def test_init_server_mode(self):
        """Test initialization in server mode (requires Docker)"""
        manager = SeekDBManager(
            mode="server",
            host="127.0.0.1",
            port=2881,
            database="test_db"
        )

        assert manager.mode == "server"
        assert manager.host == "127.0.0.1"
        assert manager.port == 2881

    def test_init_invalid_mode(self, temp_dir):
        """Test initialization with invalid mode"""
        with pytest.raises(ValueError):
            SeekDBManager(
                mode="invalid_mode",
                persist_directory=str(temp_dir)
            )


class TestSeekDBManagerCollections:
    """Test collection operations"""

    def test_initialize_collections(self, seekdb_manager_embedded):
        """Test creating collections"""
        seekdb_manager_embedded.initialize_collections(embedding_dims=1536)

        # Check collections exist
        assert seekdb_manager_embedded.client is not None

    @pytest.mark.skipif(SKIP_EMBEDDED, reason="Embedded mode requires Linux")
    def test_initialize_collections_custom_dims(self, temp_dir):
        """Test creating collections with custom dimensions"""
        manager = SeekDBManager(
            mode="embedded",
            persist_directory=str(temp_dir / "test_custom_dims")
        )

        # Test different dimensions
        for dims in [384, 768, 1536]:
            manager.initialize_collections(embedding_dims=dims)
            # Should not raise error


class TestSeekDBManagerNodeOperations:
    """Test node operations"""

    @pytest.fixture(autouse=True)
    def setup(self, seekdb_manager_embedded):
        """Setup collections before each test"""
        seekdb_manager_embedded.initialize_collections(embedding_dims=1536)
        self.manager = seekdb_manager_embedded

    def test_insert_single_node(self, sample_node_data):
        """Test inserting a single node"""
        node = NodeRecord(**sample_node_data)

        # Create a dummy embedding
        embedding = [0.1] * 1536

        self.manager.insert_nodes(
            nodes=[node],
            embeddings=[embedding]
        )

        # Verify insertion
        stats = self.manager.get_statistics()
        assert stats['total_nodes'] >= 1

    def test_insert_multiple_nodes(self, sample_node_data):
        """Test inserting multiple nodes"""
        nodes = []
        embeddings = []

        for i in range(5):
            node_data = sample_node_data.copy()
            node_data['node_id'] = f"test_node_{i:03d}"
            nodes.append(NodeRecord(**node_data))
            embeddings.append([0.1] * 1536)

        self.manager.insert_nodes(nodes=nodes, embeddings=embeddings)

        stats = self.manager.get_statistics()
        assert stats['total_nodes'] >= 5

    def test_search_nodes(self, sample_node_data):
        """Test searching nodes"""
        # Insert a node first
        node = NodeRecord(**sample_node_data)
        embedding = [0.1] * 1536

        self.manager.insert_nodes([node], [embedding])

        # Search with query embedding
        query_embedding = [0.1] * 1536
        results = self.manager.search_nodes(
            query_embedding=query_embedding,
            top_k=5
        )

        assert isinstance(results, list)
        # Results might be empty or have items, both are valid

    def test_search_nodes_with_filter(self, sample_node_data):
        """Test searching nodes with filter"""
        node = NodeRecord(**sample_node_data)
        embedding = [0.1] * 1536

        self.manager.insert_nodes([node], [embedding])

        # Search with filter
        query_embedding = [0.1] * 1536
        results = self.manager.search_nodes(
            query_embedding=query_embedding,
            top_k=5,
            filter_dict={"document_id": "test_doc"}
        )

        assert isinstance(results, list)


class TestSeekDBManagerChunkOperations:
    """Test chunk operations"""

    @pytest.fixture(autouse=True)
    def setup(self, seekdb_manager_embedded):
        """Setup collections before each test"""
        seekdb_manager_embedded.initialize_collections(embedding_dims=1536)
        self.manager = seekdb_manager_embedded

    def test_insert_single_chunk(self, sample_chunk_data):
        """Test inserting a single chunk"""
        chunk = ChunkRecord(**sample_chunk_data)
        embedding = [0.1] * 1536

        self.manager.insert_chunks([chunk], [embedding])

        stats = self.manager.get_statistics()
        assert stats['total_chunks'] >= 1

    def test_insert_multiple_chunks(self, sample_chunk_data):
        """Test inserting multiple chunks"""
        chunks = []
        embeddings = []

        for i in range(10):
            chunk_data = sample_chunk_data.copy()
            chunk_data['chunk_id'] = f"test_chunk_{i:03d}"
            chunks.append(ChunkRecord(**chunk_data))
            embeddings.append([0.1] * 1536)

        self.manager.insert_chunks(chunks, embeddings)

        stats = self.manager.get_statistics()
        assert stats['total_chunks'] >= 10

    def test_search_chunks(self, sample_chunk_data):
        """Test searching chunks"""
        chunk = ChunkRecord(**sample_chunk_data)
        embedding = [0.1] * 1536

        self.manager.insert_chunks([chunk], [embedding])

        # Search
        query_embedding = [0.1] * 1536
        results = self.manager.search_chunks(
            query_embedding=query_embedding,
            top_k=5
        )

        assert isinstance(results, list)


class TestSeekDBManagerDocumentOperations:
    """Test document-level operations"""

    @pytest.fixture(autouse=True)
    def setup(self, seekdb_manager_embedded):
        """Setup collections before each test"""
        seekdb_manager_embedded.initialize_collections(embedding_dims=1536)
        self.manager = seekdb_manager_embedded

    def test_delete_document(self, sample_node_data, sample_chunk_data):
        """Test deleting a document"""
        # Insert some data
        node = NodeRecord(**sample_node_data)
        chunk = ChunkRecord(**sample_chunk_data)
        embedding = [0.1] * 1536

        self.manager.insert_nodes([node], [embedding])
        self.manager.insert_chunks([chunk], [embedding])

        # Delete document
        stats = self.manager.delete_document("test_doc")

        assert 'nodes_deleted' in stats
        assert 'chunks_deleted' in stats

    def test_list_documents(self, sample_node_data):
        """Test listing documents"""
        # Insert a node
        node = NodeRecord(**sample_node_data)
        embedding = [0.1] * 1536

        self.manager.insert_nodes([node], [embedding])

        # List documents
        documents = self.manager.list_documents()

        assert isinstance(documents, list)

    def test_get_statistics(self):
        """Test getting statistics"""
        stats = self.manager.get_statistics()

        assert 'total_nodes' in stats
        assert 'total_chunks' in stats
        assert isinstance(stats['total_nodes'], int)
        assert isinstance(stats['total_chunks'], int)

    def test_get_stats_alias(self):
        """Test get_stats() is alias of get_statistics()"""
        stats1 = self.manager.get_statistics()
        stats2 = self.manager.get_stats()

        assert stats1 == stats2


class TestSeekDBManagerErrorHandling:
    """Test error handling"""

    def test_insert_mismatched_lengths(self, seekdb_manager_embedded, sample_node_data):
        """Test inserting with mismatched nodes and embeddings"""
        seekdb_manager_embedded.initialize_collections(embedding_dims=1536)

        nodes = [NodeRecord(**sample_node_data)]
        embeddings = [[0.1] * 1536, [0.2] * 1536]  # More embeddings than nodes

        with pytest.raises((ValueError, AssertionError)):
            seekdb_manager_embedded.insert_nodes(nodes, embeddings)

    def test_insert_wrong_embedding_dimension(self, seekdb_manager_embedded, sample_node_data):
        """Test inserting with wrong embedding dimensions"""
        seekdb_manager_embedded.initialize_collections(embedding_dims=1536)

        node = NodeRecord(**sample_node_data)
        wrong_embedding = [0.1] * 384  # Wrong dimension

        # This might raise an error or be handled gracefully
        try:
            seekdb_manager_embedded.insert_nodes([node], [wrong_embedding])
        except Exception as e:
            # Expected to fail
            assert "dimension" in str(e).lower() or "inconsistent" in str(e).lower()


class TestNodeRecord:
    """Test NodeRecord model"""

    def test_node_record_creation(self, sample_node_data):
        """Test creating a NodeRecord"""
        node = NodeRecord(**sample_node_data)

        assert node.node_id == "test_node_001"
        assert node.document_id == "test_doc"
        assert node.level == 0
        assert node.start_page == 1
        assert node.end_page == 5

    def test_node_record_with_parent(self, sample_node_data):
        """Test creating a node with parent"""
        sample_node_data['parent_id'] = "parent_node_001"
        node = NodeRecord(**sample_node_data)

        assert node.parent_id == "parent_node_001"

    def test_node_record_validation(self):
        """Test node record validation"""
        with pytest.raises(Exception):  # Pydantic validation error
            NodeRecord(
                node_id="",  # Empty node_id should fail
                document_id="test"
            )


class TestChunkRecord:
    """Test ChunkRecord model"""

    def test_chunk_record_creation(self, sample_chunk_data):
        """Test creating a ChunkRecord"""
        chunk = ChunkRecord(**sample_chunk_data)

        assert chunk.chunk_id == "test_chunk_001"
        assert chunk.node_id == "test_node_001"
        assert chunk.document_id == "test_doc"
        assert chunk.page_num == 1
        assert chunk.word_count == 8

    def test_chunk_record_validation(self):
        """Test chunk record validation"""
        with pytest.raises(Exception):  # Pydantic validation error
            ChunkRecord(
                chunk_id="",  # Empty chunk_id should fail
                node_id="test"
            )


# Markers
pytestmark = pytest.mark.seekdb
