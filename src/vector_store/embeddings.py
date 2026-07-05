"""
Embedding generation and caching.

Generates embeddings for text chunks using OpenAI API with
caching and batch processing support.
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from functools import lru_cache
import asyncio
from dataclasses import dataclass
import json

import openai

from src.core.models import Config
from src.core.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


@dataclass
class Embedding:
    """Represents a single embedding."""

    text: str
    embedding: List[float]
    model: str
    dimensions: int
    created_at: str = ""


class EmbeddingGenerator:
    """Generate embeddings for text chunks."""

    def __init__(self, config: Config):
        """
        Initialize embedding generator.

        Args:
            config: Application configuration

        Raises:
            EmbeddingError: If configuration invalid
        """
        self.config = config
        self.api_key = config.embeddings.api_key
        self.model = config.embeddings.model
        self.dimensions = config.embeddings.dimensions
        self.batch_size = config.embeddings.batch_size

        # Set OpenAI API key
        if not self.api_key:
            raise EmbeddingError("OpenAI API key not configured")

        openai.api_key = self.api_key

        logger.info(
            f"Initialized EmbeddingGenerator: model={self.model}, "
            f"dimensions={self.dimensions}, batch_size={self.batch_size}"
        )

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")

        try:
            logger.debug(f"Generating embedding for text (len={len(text)})")

            response = openai.Embedding.create(
                input=text,
                model=self.model,
            )

            embedding = response["data"][0]["embedding"]

            if len(embedding) != self.dimensions:
                logger.warning(
                    f"Embedding dimensions mismatch: "
                    f"expected {self.dimensions}, got {len(embedding)}"
                )

            return embedding

        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}") from e

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding fails
        """
        if not texts:
            return []

        logger.info(f"Generating embeddings for {len(texts)} texts")

        try:
            # Filter out empty texts
            valid_texts = [t for t in texts if t and t.strip()]

            if not valid_texts:
                logger.warning("No valid texts to embed")
                return []

            # OpenAI API can handle multiple inputs at once
            response = openai.Embedding.create(
                input=valid_texts,
                model=self.model,
            )

            # Extract embeddings in order
            embeddings = [None] * len(valid_texts)
            for item in response["data"]:
                idx = item["index"]
                embeddings[idx] = item["embedding"]

            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings

        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            raise EmbeddingError(f"Failed to generate embeddings: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise EmbeddingError(f"Failed to generate embeddings: {str(e)}") from e

    async def embed_texts_async(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings asynchronously.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # For now, run synchronously in thread pool
        # Can be enhanced with async OpenAI client in future
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_texts, texts)

    def embed_chunks_batch(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for chunks in batches.

        Args:
            chunks: List of chunk dictionaries with 'text' key

        Returns:
            List of chunks with added 'embedding' key

        Raises:
            EmbeddingError: If any batch fails
        """
        logger.info(f"Processing {len(chunks)} chunks in batches of {self.batch_size}")

        result = []
        total_batches = (len(chunks) + self.batch_size - 1) // self.batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min((batch_idx + 1) * self.batch_size, len(chunks))
            batch = chunks[start_idx:end_idx]

            logger.debug(f"Processing batch {batch_idx + 1}/{total_batches}")

            # Extract texts
            texts = [chunk["text"] for chunk in batch]

            # Generate embeddings
            embeddings = self.embed_texts(texts)

            # Add embeddings to chunks
            for chunk, embedding in zip(batch, embeddings):
                chunk["embedding"] = embedding
                result.append(chunk)

        logger.info(f"Successfully embedded {len(result)} chunks")
        return result

    def get_text_hash(self, text: str) -> str:
        """
        Get deterministic hash for text (for caching).

        Args:
            text: Text to hash

        Returns:
            SHA256 hash
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        Validate embedding vector.

        Args:
            embedding: Embedding to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(embedding, list):
            return False

        if len(embedding) != self.dimensions:
            return False

        # Check all elements are floats
        return all(isinstance(x, (int, float)) for x in embedding)
