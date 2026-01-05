"""
Unit tests for EmbeddingManager
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np

from src.embedding_manager import EmbeddingManager


class TestEmbeddingManager:
    """Test EmbeddingManager class"""

    def test_init(self, test_config):
        """Test initialization"""
        manager = EmbeddingManager(
            api_key=test_config["api_key"],
            model=test_config["model"],
            base_url=test_config["base_url"]
        )

        # Check that client and model are set correctly (api_key and base_url are not stored)
        assert manager.client is not None
        assert manager.model == test_config["model"]
        assert manager.batch_size == 100  # default

    def test_init_without_base_url(self, test_config):
        """Test initialization without custom base_url"""
        manager = EmbeddingManager(
            api_key=test_config["api_key"],
            model=test_config["model"]
        )

        # base_url is not stored, but client should be created
        assert manager.client is not None
        assert manager.model == test_config["model"]

    @pytest.mark.parametrize("batch_size", [1, 5, 10, 25])
    def test_batch_size_configuration(self, test_config, batch_size):
        """Test different batch sizes"""
        manager = EmbeddingManager(
            api_key=test_config["api_key"],
            model=test_config["model"],
            batch_size=batch_size
        )

        assert manager.batch_size == batch_size

    @pytest.mark.integration
    def test_embed_single_text(self, embedding_manager, sample_text):
        """Test embedding a single text (integration test)"""
        embedding = embedding_manager.embed(sample_text)

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.integration
    def test_embed_batch(self, embedding_manager, sample_texts):
        """Test embedding multiple texts (integration test)"""
        embeddings = embedding_manager.embed(sample_texts)

        assert embeddings is not None
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(sample_texts)

        for emb in embeddings:
            assert isinstance(emb, list)
            assert len(emb) > 0
            assert all(isinstance(x, float) for x in emb)

    @pytest.mark.integration
    def test_embedding_consistency(self, embedding_manager, sample_text):
        """Test that same text produces similar embeddings"""
        emb1 = embedding_manager.embed(sample_text)
        emb2 = embedding_manager.embed(sample_text)

        # Convert to numpy arrays for comparison
        arr1 = np.array(emb1)
        arr2 = np.array(emb2)

        # Check dimensions match
        assert arr1.shape == arr2.shape

        # Check embeddings are very similar (cosine similarity should be ~1)
        similarity = np.dot(arr1, arr2) / (np.linalg.norm(arr1) * np.linalg.norm(arr2))
        assert similarity > 0.99  # Should be nearly identical

    @pytest.mark.integration
    def test_embedding_dimension(self, embedding_manager, sample_text, test_config):
        """Test that embedding has correct dimensions"""
        embedding = embedding_manager.embed(sample_text)

        expected_dim = test_config["embedding_dims"]
        assert len(embedding) == expected_dim

    def test_embed_empty_text(self, embedding_manager):
        """Test embedding empty text"""
        with pytest.raises((ValueError, Exception)):
            embedding_manager.embed("")

    def test_embed_none(self, embedding_manager):
        """Test embedding None (treated as empty)"""
        # None is treated as empty list due to "if not text" check
        result = embedding_manager.embed(None)
        assert result == []

    @pytest.mark.integration
    def test_embed_batch_empty_list(self, embedding_manager):
        """Test embedding empty list"""
        embeddings = embedding_manager.embed([])
        assert embeddings == []

    @pytest.mark.integration
    def test_embed_very_long_text(self, embedding_manager):
        """Test embedding very long text"""
        long_text = "test " * 1000  # Very long text
        embedding = embedding_manager.embed(long_text)

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0

    @pytest.mark.integration
    def test_embed_special_characters(self, embedding_manager):
        """Test embedding text with special characters"""
        special_text = "Hello! @#$%^&*() 你好 مرحبا"
        embedding = embedding_manager.embed(special_text)

        assert embedding is not None
        assert isinstance(embedding, list)

    @pytest.mark.integration
    def test_batch_processing_large_batch(self, embedding_manager):
        """Test processing a large batch of texts"""
        # Create 50 texts (exceeds typical batch size of 25)
        large_batch = [f"Test text number {i}" for i in range(50)]

        embeddings = embedding_manager.embed(large_batch)

        assert len(embeddings) == 50
        for emb in embeddings:
            assert isinstance(emb, list)
            assert len(emb) > 0

    @patch('src.embedding_manager.OpenAI')
    def test_api_error_handling(self, mock_openai, test_config):
        """Test API error handling for batch processing"""
        # Mock API to raise error
        mock_client = Mock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        manager = EmbeddingManager(
            api_key=test_config["api_key"],
            model=test_config["model"]
        )

        # For batch processing, errors are caught and zero vectors are returned
        result = manager.embed(["test1", "test2"])
        assert isinstance(result, list)
        # Should return zero vectors as fallback
        assert len(result) == 2

    def test_repr(self, embedding_manager):
        """Test string representation"""
        repr_str = repr(embedding_manager)
        assert "EmbeddingManager" in repr_str or embedding_manager.model in repr_str


class TestEmbeddingUtilities:
    """Test utility functions related to embeddings"""

    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        arr1 = np.array(vec1)
        arr2 = np.array(vec2)

        similarity = np.dot(arr1, arr2) / (np.linalg.norm(arr1) * np.linalg.norm(arr2))
        assert abs(similarity - 1.0) < 1e-6

    def test_embedding_normalization(self):
        """Test embedding normalization"""
        vec = [3.0, 4.0, 0.0]
        arr = np.array(vec)

        normalized = arr / np.linalg.norm(arr)
        norm = np.linalg.norm(normalized)

        assert abs(norm - 1.0) < 1e-6


# Markers for running specific test groups
pytestmark = pytest.mark.embedding
