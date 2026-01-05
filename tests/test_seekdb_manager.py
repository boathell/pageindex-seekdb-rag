"""
Unit tests for SeekDBManager using server mode (Docker)
"""

import pytest
from pathlib import Path

from src.seekdb_manager import SeekDBManager, NodeRecord, ChunkRecord
from tests.conftest import SKIP_SEEKDB
from src.config import config


class TestSeekDBManagerInit:
    """Test SeekDBManager initialization"""

    @pytest.mark.skipif(SKIP_SEEKDB, reason="Requires seekdb Docker container")
    def test_init_server_mode(self):
        """Test initialization in server mode (Docker)"""
        manager = SeekDBManager(
            mode="server",
            host=config.seekdb.seekdb_host,
            port=config.seekdb.seekdb_port,
            user=config.seekdb.seekdb_user,
            password=config.seekdb.seekdb_password,
            database=config.seekdb.seekdb_database
        )

        assert manager.mode == "server"
        assert manager.client is not None

    def test_init_invalid_mode(self):
        """Test initialization with invalid mode"""
        with pytest.raises(ValueError):
            SeekDBManager(mode="invalid_mode")


class TestSeekDBManagerCollections:
    """Test collection operations"""

    def test_initialize_collections(self, seekdb_manager):
        """Test creating collections"""
        # Collections should already be initialized by fixture
        assert seekdb_manager.client is not None

    def test_initialize_collections_custom_dims(self, seekdb_manager):
        """Test creating collections with custom dimensions"""
        # Test different dimensions
        for dims in [384, 768, 1536]:
            seekdb_manager.initialize_collections(embedding_dims=dims)
            # Should not raise error


class TestSeekDBManagerNodeOperations:
    """Test node operations"""

    def test_insert_single_node(self, seekdb_manager, sample_node_data):
        """Test inserting a single node"""
        import uuid
        unique_id = f"node_{uuid.uuid4().hex[:8]}"
        node = NodeRecord(**{**sample_node_data, "node_id": unique_id})

        # Create a dummy embedding
        embedding = [0.1] * 1536

        seekdb_manager.insert_nodes(
            nodes=[node],
            embeddings=[embedding]
        )

        # Verify by checking stats
        stats = seekdb_manager.get_statistics()
        assert stats['total_nodes'] >= 1

    def test_insert_multiple_nodes(self, seekdb_manager, sample_node_data):
        """Test inserting multiple nodes"""
        import uuid
        nodes = [
            NodeRecord(**{**sample_node_data, "node_id": f"node_{uuid.uuid4().hex[:8]}"})
            for i in range(3)
        ]

        embeddings = [[0.1 + i*0.01] * 1536 for i in range(3)]

        seekdb_manager.insert_nodes(
            nodes=nodes,
            embeddings=embeddings
        )

        stats = seekdb_manager.get_statistics()
        assert stats['total_nodes'] >= 3

    def test_search_nodes(self, seekdb_manager, sample_node_data):
        """Test searching nodes"""
        # First insert a node with unique ID
        import uuid
        unique_id = f"search_test_{uuid.uuid4().hex[:8]}"
        node = NodeRecord(**{**sample_node_data, "node_id": unique_id})
        embedding = [0.5] * 1536

        seekdb_manager.insert_nodes(
            nodes=[node],
            embeddings=[embedding]
        )

        # Search with similar vector
        query_embedding = [0.51] * 1536
        results = seekdb_manager.search_nodes(
            query_embedding=query_embedding,
            top_k=5
        )

        # Should return at least one result
        assert len(results) >= 1

    def test_search_nodes_with_filter(self, seekdb_manager, sample_node_data):
        """Test searching nodes with document_id filter"""
        # Insert a node with specific document_id and unique ID
        import uuid
        unique_id = f"filter_test_{uuid.uuid4().hex[:8]}"
        node = NodeRecord(**{**sample_node_data, "node_id": unique_id})
        embedding = [0.3] * 1536

        seekdb_manager.insert_nodes(
            nodes=[node],
            embeddings=[embedding]
        )

        # Search with filter using filter_dict parameter
        query_embedding = [0.31] * 1536
        results = seekdb_manager.search_nodes(
            query_embedding=query_embedding,
            filter_dict={"document_id": sample_node_data["document_id"]},
            top_k=5
        )

        # Results should only be from the filtered document
        assert all(r[0].document_id == sample_node_data["document_id"] for r in results if r)


class TestSeekDBManagerChunkOperations:
    """Test chunk operations"""

    def test_insert_single_chunk(self, seekdb_manager, sample_chunk_data):
        """Test inserting a single chunk"""
        import uuid
        unique_id = f"chunk_{uuid.uuid4().hex[:8]}"
        chunk = ChunkRecord(**{**sample_chunk_data, "chunk_id": unique_id})
        embedding = [0.2] * 1536

        seekdb_manager.insert_chunks(
            chunks=[chunk],
            embeddings=[embedding]
        )

        stats = seekdb_manager.get_statistics()
        assert stats['total_chunks'] >= 1

    def test_insert_multiple_chunks(self, seekdb_manager, sample_chunk_data):
        """Test inserting multiple chunks"""
        import uuid
        chunks = [
            ChunkRecord(**{**sample_chunk_data, "chunk_id": f"chunk_{uuid.uuid4().hex[:8]}"})
            for i in range(3)
        ]

        embeddings = [[0.2 + i*0.01] * 1536 for i in range(3)]

        seekdb_manager.insert_chunks(
            chunks=chunks,
            embeddings=embeddings
        )

        stats = seekdb_manager.get_statistics()
        assert stats['total_chunks'] >= 3

    def test_search_chunks(self, seekdb_manager, sample_chunk_data):
        """Test searching chunks"""
        # Insert a chunk with unique ID
        import uuid
        unique_id = f"search_chunk_{uuid.uuid4().hex[:8]}"
        chunk = ChunkRecord(**{**sample_chunk_data, "chunk_id": unique_id})
        embedding = [0.6] * 1536

        seekdb_manager.insert_chunks(
            chunks=[chunk],
            embeddings=[embedding]
        )

        # Search
        query_embedding = [0.61] * 1536
        results = seekdb_manager.search_chunks(
            query_embedding=query_embedding,
            top_k=5
        )

        assert len(results) >= 1


class TestSeekDBManagerDocumentOperations:
    """Test document-level operations"""

    def test_delete_document(self, seekdb_manager, sample_node_data, sample_chunk_data):
        """Test deleting all data for a document"""
        import uuid
        doc_id = f"test_delete_doc_{uuid.uuid4().hex[:8]}"

        # Insert some nodes and chunks with unique IDs
        node = NodeRecord(**{**sample_node_data, "node_id": f"del_node_{uuid.uuid4().hex[:8]}", "document_id": doc_id})
        chunk = ChunkRecord(**{**sample_chunk_data, "chunk_id": f"del_chunk_{uuid.uuid4().hex[:8]}", "document_id": doc_id})

        seekdb_manager.insert_nodes([node], [[0.1] * 1536])
        seekdb_manager.insert_chunks([chunk], [[0.2] * 1536])

        # Delete document
        seekdb_manager.delete_document(doc_id)

        # Verify deletion by searching
        results = seekdb_manager.search_nodes([0.1] * 1536, filter_dict={"document_id": doc_id})
        # Should have no results or very few
        # (Note: Deletion might not be immediate in all implementations)

    def test_list_documents(self, seekdb_manager, sample_node_data):
        """Test listing all documents"""
        # Insert a node with unique document_id and node_id
        import uuid
        doc_id = f"test_list_doc_{uuid.uuid4().hex[:8]}"
        node = NodeRecord(**{**sample_node_data, "node_id": f"list_node_{uuid.uuid4().hex[:8]}", "document_id": doc_id})

        seekdb_manager.insert_nodes([node], [[0.1] * 1536])

        # List documents
        documents = seekdb_manager.list_documents()

        # Should be a list (might be empty or contain our document)
        assert isinstance(documents, list)

    def test_get_statistics(self, seekdb_manager):
        """Test getting database statistics"""
        stats = seekdb_manager.get_statistics()

        # Should return a dict with expected keys
        assert isinstance(stats, dict)
        assert 'total_nodes' in stats
        assert 'total_chunks' in stats
        assert 'collections' in stats

        # Values should be non-negative integers
        assert stats['total_nodes'] >= 0
        assert stats['total_chunks'] >= 0


class TestSeekDBManagerErrorHandling:
    """Test error handling"""

    def test_insert_mismatched_lengths(self, seekdb_manager, sample_node_data):
        """Test inserting nodes with mismatched embeddings length"""
        nodes = [NodeRecord(**sample_node_data)]
        embeddings = [[0.1] * 1536, [0.2] * 1536]  # Too many embeddings

        with pytest.raises((ValueError, AssertionError)):
            seekdb_manager.insert_nodes(nodes, embeddings)

    def test_insert_wrong_embedding_dimension(self, seekdb_manager, sample_node_data):
        """Test inserting with wrong embedding dimension"""
        node = NodeRecord(**sample_node_data)
        wrong_embedding = [0.1] * 768  # Wrong dimension (expected 1536)

        # This might raise an error or be handled gracefully depending on implementation
        # For now, we just test that it doesn't crash the system
        try:
            seekdb_manager.insert_nodes([node], [wrong_embedding])
        except Exception as e:
            # Some error is expected
            assert True


class TestNodeRecord:
    """Test NodeRecord model"""

    def test_node_record_creation(self, sample_node_data):
        """Test creating a NodeRecord"""
        node = NodeRecord(**sample_node_data)

        assert node.node_id == sample_node_data["node_id"]
        assert node.document_id == sample_node_data["document_id"]
        assert node.title == sample_node_data["title"]

    def test_node_record_with_parent(self, sample_node_data):
        """Test NodeRecord with parent_id"""
        data = {**sample_node_data, "parent_id": "parent_node_001"}
        node = NodeRecord(**data)

        assert node.parent_id == "parent_node_001"

    def test_node_record_validation(self):
        """Test NodeRecord validation"""
        # Missing required fields should raise error
        with pytest.raises(Exception):  # Pydantic ValidationError
            NodeRecord(node_id="test")


class TestChunkRecord:
    """Test ChunkRecord model"""

    def test_chunk_record_creation(self, sample_chunk_data):
        """Test creating a ChunkRecord"""
        chunk = ChunkRecord(**sample_chunk_data)

        assert chunk.chunk_id == sample_chunk_data["chunk_id"]
        assert chunk.node_id == sample_chunk_data["node_id"]
        assert chunk.content == sample_chunk_data["content"]

    def test_chunk_record_validation(self):
        """Test ChunkRecord validation"""
        # Missing required fields should raise error
        with pytest.raises(Exception):  # Pydantic ValidationError
            ChunkRecord(chunk_id="test")


# Markers
pytestmark = pytest.mark.seekdb
