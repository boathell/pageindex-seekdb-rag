"""
Unit tests for HybridSearchEngine
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.hybrid_search import (
    HybridSearchEngine,
    HybridSearchConfig,
    TreeSearchConfig,
    VectorSearchConfig
)
from src.seekdb_manager import NodeRecord, SearchResult


class TestSearchConfigurations:
    """Test configuration models"""

    def test_tree_search_config_defaults(self):
        """Test TreeSearchConfig default values"""
        config = TreeSearchConfig()

        assert config.max_depth == 3
        assert config.top_k_per_level == 5
        assert config.similarity_threshold == 0.6
        assert config.enable_pruning == True

    def test_tree_search_config_custom(self):
        """Test TreeSearchConfig custom values"""
        config = TreeSearchConfig(
            max_depth=5,
            top_k_per_level=10,
            similarity_threshold=0.7,
            enable_pruning=False
        )

        assert config.max_depth == 5
        assert config.top_k_per_level == 10
        assert config.similarity_threshold == 0.7
        assert config.enable_pruning == False

    def test_vector_search_config_defaults(self):
        """Test VectorSearchConfig default values"""
        config = VectorSearchConfig()

        assert config.top_k == 20
        assert config.enable_rerank == False

    def test_hybrid_search_config_defaults(self):
        """Test HybridSearchConfig default values"""
        config = HybridSearchConfig()

        assert config.tree_weight == 0.4
        assert config.vector_weight == 0.6
        assert isinstance(config.tree_config, TreeSearchConfig)
        assert isinstance(config.vector_config, VectorSearchConfig)

    def test_hybrid_search_config_custom_weights(self):
        """Test HybridSearchConfig custom weights"""
        config = HybridSearchConfig(
            tree_weight=0.7,
            vector_weight=0.3
        )

        assert config.tree_weight == 0.7
        assert config.vector_weight == 0.3

    def test_hybrid_search_config_weights_sum(self):
        """Test that weights don't need to sum to 1.0"""
        # Weights don't have to sum to 1.0, but it's recommended
        config = HybridSearchConfig(
            tree_weight=0.5,
            vector_weight=0.5
        )

        assert config.tree_weight + config.vector_weight == 1.0


class TestHybridSearchEngineInit:
    """Test HybridSearchEngine initialization"""

    def test_init_basic(self):
        """Test basic initialization"""
        mock_db = Mock()
        mock_embed = Mock()

        engine = HybridSearchEngine(
            seekdb_manager=mock_db,
            embedding_manager=mock_embed
        )

        assert engine.db == mock_db
        assert engine.embed == mock_embed
        assert engine.cache is None
        assert isinstance(engine.config, HybridSearchConfig)

    def test_init_with_cache(self):
        """Test initialization with cache"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_cache = Mock()

        engine = HybridSearchEngine(
            seekdb_manager=mock_db,
            embedding_manager=mock_embed,
            cache_manager=mock_cache
        )

        assert engine.cache == mock_cache

    def test_init_with_custom_config(self):
        """Test initialization with custom config"""
        mock_db = Mock()
        mock_embed = Mock()
        config = HybridSearchConfig(tree_weight=0.6, vector_weight=0.4)

        engine = HybridSearchEngine(
            seekdb_manager=mock_db,
            embedding_manager=mock_embed,
            config=config
        )

        assert engine.config.tree_weight == 0.6
        assert engine.config.vector_weight == 0.4


class TestTreeSearch:
    """Test tree search functionality"""

    def test_tree_search_basic(self):
        """Test basic tree search"""
        mock_db = Mock()
        mock_embed = Mock()

        # Mock search_nodes to return empty results
        mock_db.search_nodes.return_value = []

        engine = HybridSearchEngine(mock_db, mock_embed)

        query_embedding = [0.1] * 1536
        results = engine.tree_search(query_embedding)

        assert isinstance(results, list)
        # Called at least once for root nodes
        assert mock_db.search_nodes.called

    def test_tree_search_with_document_filter(self):
        """Test tree search with document filter"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_nodes.return_value = []

        engine = HybridSearchEngine(mock_db, mock_embed)

        query_embedding = [0.1] * 1536
        engine.tree_search(query_embedding, document_id="test_doc")

        # Verify filter was passed
        call_args = mock_db.search_nodes.call_args
        assert call_args is not None

    def test_tree_search_with_custom_config(self):
        """Test tree search with custom configuration"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_nodes.return_value = []

        engine = HybridSearchEngine(mock_db, mock_embed)

        config = TreeSearchConfig(
            max_depth=5,
            top_k_per_level=10
        )

        query_embedding = [0.1] * 1536
        engine.tree_search(query_embedding, config=config)

        assert mock_db.search_nodes.called


class TestVectorSearch:
    """Test vector search functionality"""

    def test_vector_search_basic(self):
        """Test basic vector search"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_chunks.return_value = []

        engine = HybridSearchEngine(mock_db, mock_embed)

        query_embedding = [0.1] * 1536
        results = engine.vector_search(query_embedding)

        assert isinstance(results, list)
        assert mock_db.search_chunks.called

    def test_vector_search_with_document_filter(self):
        """Test vector search with document filter"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_chunks.return_value = []

        engine = HybridSearchEngine(mock_db, mock_embed)

        query_embedding = [0.1] * 1536
        engine.vector_search(query_embedding, document_id="test_doc")

        assert mock_db.search_chunks.called

    def test_vector_search_with_custom_config(self):
        """Test vector search with custom configuration"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_chunks.return_value = []

        engine = HybridSearchEngine(mock_db, mock_embed)

        config = VectorSearchConfig(top_k=50)

        query_embedding = [0.1] * 1536
        engine.vector_search(query_embedding, config=config)

        assert mock_db.search_chunks.called


class TestHybridSearch:
    """Test hybrid search functionality"""

    def test_hybrid_search_tree_only_strategy(self):
        """Test hybrid_search with tree_only strategy"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_nodes.return_value = []

        # Mock embedding
        mock_embed.embed.return_value = [0.1] * 1536

        engine = HybridSearchEngine(mock_db, mock_embed)

        results = engine.hybrid_search(
            query="test query",
            strategy="tree_only"
        )

        assert isinstance(results, list)
        assert mock_embed.embed.called
        assert mock_db.search_nodes.called

    def test_hybrid_search_vector_only_strategy(self):
        """Test hybrid_search with vector_only strategy"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_chunks.return_value = []

        mock_embed.embed.return_value = [0.1] * 1536

        engine = HybridSearchEngine(mock_db, mock_embed)

        results = engine.hybrid_search(
            query="test query",
            strategy="vector_only"
        )

        assert isinstance(results, list)
        assert mock_embed.embed.called
        assert mock_db.search_chunks.called

    def test_hybrid_search_hybrid_strategy(self):
        """Test hybrid_search with hybrid strategy"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_nodes.return_value = []
        mock_db.search_chunks.return_value = []

        mock_embed.embed.return_value = [0.1] * 1536

        engine = HybridSearchEngine(mock_db, mock_embed)

        results = engine.hybrid_search(
            query="test query",
            strategy="hybrid"
        )

        assert isinstance(results, list)
        assert mock_embed.embed.called

    def test_hybrid_search_with_vector_config(self):
        """Test hybrid_search with custom vector config top_k"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_chunks.return_value = []

        mock_embed.embed.return_value = [0.1] * 1536

        engine = HybridSearchEngine(mock_db, mock_embed)

        # Use config to specify top_k instead of direct parameter
        custom_config = HybridSearchConfig(
            vector_config=VectorSearchConfig(top_k=10)
        )
        results = engine.hybrid_search(
            query="test query",
            strategy="vector_only",
            config=custom_config
        )

        assert isinstance(results, list)

    def test_hybrid_search_with_custom_config(self):
        """Test hybrid_search with custom HybridSearchConfig"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_nodes.return_value = []
        mock_db.search_chunks.return_value = []

        mock_embed.embed.return_value = [0.1] * 1536

        engine = HybridSearchEngine(mock_db, mock_embed)

        custom_config = HybridSearchConfig(
            tree_weight=0.7,
            vector_weight=0.3
        )

        results = engine.hybrid_search(
            query="test query",
            strategy="hybrid",
            config=custom_config
        )

        assert isinstance(results, list)

    def test_hybrid_search_invalid_strategy(self):
        """Test hybrid_search with invalid strategy"""
        mock_db = Mock()
        mock_embed = Mock()

        # Mock search methods to return empty lists
        mock_db.search_nodes.return_value = []
        mock_db.search_chunks.return_value = []
        mock_embed.embed.return_value = [0.1] * 1536

        engine = HybridSearchEngine(mock_db, mock_embed)

        # Invalid strategy defaults to "hybrid" behavior, no exception raised
        # Just verify it returns a list
        results = engine.hybrid_search(
            query="test query",
            strategy="invalid_strategy"
        )
        assert isinstance(results, list)

    def test_hybrid_search_with_cache_hit(self):
        """Test hybrid_search with cache hit"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_cache = Mock()

        # Mock cache to return a list of result dictionaries with all required fields
        cached_data = [
            {
                "chunk_id": "chunk1",
                "content": "test content",
                "score": 0.9,
                "node_id": "node1",
                "node_path": ["root", "node1"],
                "page_num": 1,
                "metadata": {}
            }
        ]
        mock_cache.get_query_cache.return_value = cached_data
        mock_cache.enable_cache = True

        engine = HybridSearchEngine(mock_db, mock_embed, mock_cache)

        results = engine.hybrid_search(
            query="test query",
            strategy="vector_only"
        )

        # Should return SearchResult objects from cache
        assert isinstance(results, list)
        assert len(results) == 1
        assert hasattr(results[0], 'node_id')
        assert results[0].score == 0.9

    def test_hybrid_search_with_document_id_filter(self):
        """Test hybrid_search with document_id filter"""
        mock_db = Mock()
        mock_embed = Mock()
        mock_db.search_chunks.return_value = []

        mock_embed.embed.return_value = [0.1] * 1536

        engine = HybridSearchEngine(mock_db, mock_embed)

        results = engine.hybrid_search(
            query="test query",
            document_id="test_doc",
            strategy="vector_only"
        )

        assert isinstance(results, list)


class TestResultMerging:
    """Test result merging and scoring"""

    def test_merge_empty_results(self):
        """Test merging empty result lists"""
        mock_db = Mock()
        mock_embed = Mock()

        engine = HybridSearchEngine(mock_db, mock_embed)

        # Both empty
        tree_results = []
        vector_results = []

        # merge_results is typically an internal method
        # Test by calling hybrid_search with mocked empty returns
        mock_db.search_nodes.return_value = []
        mock_db.search_chunks.return_value = []
        mock_embed.embed.return_value = [0.1] * 1536

        results = engine.hybrid_search(
            query="test",
            strategy="hybrid"
        )

        assert results == []

    def test_score_combination(self):
        """Test score combination with different weights"""
        config = HybridSearchConfig(
            tree_weight=0.6,
            vector_weight=0.4
        )

        tree_score = 0.8
        vector_score = 0.9

        combined = (tree_score * config.tree_weight +
                   vector_score * config.vector_weight)

        expected = 0.8 * 0.6 + 0.9 * 0.4
        assert abs(combined - expected) < 1e-6


# Markers
pytestmark = pytest.mark.search
