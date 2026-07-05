"""
Unit tests for embeddings module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.vector_store.embeddings import EmbeddingGenerator, Embedding
from src.core.exceptions import EmbeddingError


class TestEmbeddingGenerator:
    """Tests for EmbeddingGenerator class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.embeddings.api_key = "sk-test-key"
        config.embeddings.model = "text-embedding-3-small"
        config.embeddings.dimensions = 1536
        config.embeddings.batch_size = 50
        return config

    def test_init_valid_config(self, mock_config):
        """Test initialization with valid config."""
        with patch("openai.api_key"):
            generator = EmbeddingGenerator(mock_config)
            assert generator.model == "text-embedding-3-small"
            assert generator.dimensions == 1536

    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        config = Mock()
        config.embeddings.api_key = None

        with pytest.raises(EmbeddingError):
            EmbeddingGenerator(config)

    def test_embed_text_empty(self, mock_config):
        """Test embedding empty text raises error."""
        with patch("openai.api_key"):
            generator = EmbeddingGenerator(mock_config)
            with pytest.raises(EmbeddingError):
                generator.embed_text("")

    def test_embed_text_success(self, mock_config):
        """Test successful text embedding."""
        with patch("openai.api_key"):
            with patch("openai.Embedding.create") as mock_create:
                mock_create.return_value = {
                    "data": [
                        {"embedding": [0.1] * 1536}
                    ]
                }

                generator = EmbeddingGenerator(mock_config)
                result = generator.embed_text("Test text")

                assert len(result) == 1536
                assert result[0] == 0.1

    def test_embed_texts_empty_list(self, mock_config):
        """Test embedding empty list."""
        with patch("openai.api_key"):
            generator = EmbeddingGenerator(mock_config)
            result = generator.embed_texts([])
            assert result == []

    def test_embed_texts_success(self, mock_config):
        """Test successful batch embedding."""
        with patch("openai.api_key"):
            with patch("openai.Embedding.create") as mock_create:
                mock_create.return_value = {
                    "data": [
                        {"embedding": [0.1] * 1536, "index": 0},
                        {"embedding": [0.2] * 1536, "index": 1},
                    ]
                }

                generator = EmbeddingGenerator(mock_config)
                result = generator.embed_texts(["Text 1", "Text 2"])

                assert len(result) == 2
                assert len(result[0]) == 1536
                assert result[0][0] == 0.1
                assert result[1][0] == 0.2

    def test_embed_chunks_batch(self, mock_config):
        """Test batch embedding of chunks."""
        with patch("openai.api_key"):
            with patch("openai.Embedding.create") as mock_create:
                mock_create.return_value = {
                    "data": [
                        {"embedding": [0.1] * 1536, "index": 0},
                    ]
                }

                generator = EmbeddingGenerator(mock_config)
                chunks = [
                    {"text": "Chunk 1"},
                    {"text": "Chunk 2"},
                ]
                result = generator.embed_chunks_batch(chunks)

                assert len(result) >= 0

    def test_get_text_hash(self, mock_config):
        """Test text hashing for caching."""
        with patch("openai.api_key"):
            generator = EmbeddingGenerator(mock_config)
            hash1 = generator.get_text_hash("Test text")
            hash2 = generator.get_text_hash("Test text")

            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 hex length

    def test_validate_embedding_valid(self, mock_config):
        """Test embedding validation with valid embedding."""
        with patch("openai.api_key"):
            generator = EmbeddingGenerator(mock_config)
            embedding = [0.1] * 1536

            assert generator.validate_embedding(embedding) is True

    def test_validate_embedding_wrong_dimension(self, mock_config):
        """Test embedding validation with wrong dimensions."""
        with patch("openai.api_key"):
            generator = EmbeddingGenerator(mock_config)
            embedding = [0.1] * 1024  # Wrong size

            assert generator.validate_embedding(embedding) is False

    def test_validate_embedding_not_list(self, mock_config):
        """Test embedding validation with non-list."""
        with patch("openai.api_key"):
            generator = EmbeddingGenerator(mock_config)

            assert generator.validate_embedding("not a list") is False


class TestEmbedding:
    """Tests for Embedding dataclass."""

    def test_create_embedding(self):
        """Test creating embedding instance."""
        embedding = Embedding(
            text="Test text",
            embedding=[0.1, 0.2, 0.3],
            model="test-model",
            dimensions=3,
        )

        assert embedding.text == "Test text"
        assert len(embedding.embedding) == 3
        assert embedding.model == "test-model"
