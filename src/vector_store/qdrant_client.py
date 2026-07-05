"""
Qdrant vector database client and operations.

Manages connections to Qdrant and performs CRUD operations
for storing and retrieving embedded chunks.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from src.core.models import Config
from src.core.exceptions import VectorDatabaseError

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result from vector database."""

    point_id: int
    score: float
    payload: Dict[str, Any]


class QdrantVectorStore:
    """Vector store using Qdrant."""

    def __init__(self, config: Config):
        """
        Initialize Qdrant client.

        Args:
            config: Application configuration

        Raises:
            VectorDatabaseError: If connection fails
        """
        self.config = config
        self.url = config.vector_db.url
        self.api_key = config.vector_db.api_key
        self.collection_name = config.vector_db.collection_name
        self.vector_size = config.vector_db.vector_size
        self.distance_metric = config.vector_db.distance_metric

        try:
            logger.info(f"Connecting to Qdrant at {self.url}")

            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=config.vector_db.timeout,
            )

            # Verify connection
            self.client.get_collections()

            logger.info("Successfully connected to Qdrant")

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Qdrant connection failed: {str(e)}") from e

    def create_collection(self) -> bool:
        """
        Create collection if it doesn't exist.

        Returns:
            True if created or already exists, False if error

        Raises:
            VectorDatabaseError: If creation fails
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name in collection_names:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return True

            # Map distance metric
            if self.distance_metric.lower() == "cosine":
                distance = Distance.COSINE
            elif self.distance_metric.lower() == "euclidean":
                distance = Distance.EUCLID
            else:
                distance = Distance.DOT

            # Create collection
            logger.info(
                f"Creating collection '{self.collection_name}' "
                f"with vector_size={self.vector_size}, metric={distance}"
            )

            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=distance,
                ),
            )

            logger.info(f"Successfully created collection '{self.collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create collection: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Collection creation failed: {str(e)}") from e

    def add_points(self, points: List[Dict[str, Any]]) -> int:
        """
        Add points (embeddings) to collection.

        Args:
            points: List of point dictionaries with:
                - id: unique identifier
                - vector: embedding vector
                - payload: metadata dictionary

        Returns:
            Number of points added

        Raises:
            VectorDatabaseError: If operation fails
        """
        if not points:
            logger.warning("No points to add")
            return 0

        try:
            logger.info(f"Adding {len(points)} points to collection")

            # Convert to Qdrant PointStruct
            qdrant_points = [
                PointStruct(
                    id=int(p["id"]),
                    vector=p["vector"],
                    payload=p.get("payload", {}),
                )
                for p in points
            ]

            # Upload to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=qdrant_points,
            )

            logger.info(f"Successfully added {len(points)} points")
            return len(points)

        except Exception as e:
            logger.error(f"Failed to add points: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to add points: {str(e)}") from e

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of SearchResult objects

        Raises:
            VectorDatabaseError: If search fails
        """
        try:
            logger.debug(f"Searching for {limit} similar vectors")

            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            # Convert to SearchResult objects
            search_results = [
                SearchResult(
                    point_id=result.id,
                    score=result.score,
                    payload=result.payload,
                )
                for result in results
            ]

            logger.debug(f"Found {len(search_results)} similar vectors")
            return search_results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Search failed: {str(e)}") from e

    def delete_point(self, point_id: int) -> bool:
        """
        Delete a point from collection.

        Args:
            point_id: Point ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            VectorDatabaseError: If operation fails
        """
        try:
            logger.debug(f"Deleting point {point_id}")

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    idxs=[point_id],
                ),
            )

            logger.debug(f"Successfully deleted point {point_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete point: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to delete point: {str(e)}") from e

    def delete_collection(self) -> bool:
        """
        Delete entire collection.

        Returns:
            True if deleted

        Raises:
            VectorDatabaseError: If operation fails
        """
        try:
            logger.warning(f"Deleting collection '{self.collection_name}'")

            self.client.delete_collection(collection_name=self.collection_name)

            logger.info(f"Successfully deleted collection '{self.collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to delete collection: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to delete collection: {str(e)}") from e

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get collection statistics and info.

        Returns:
            Dictionary with collection information

        Raises:
            VectorDatabaseError: If operation fails
        """
        try:
            logger.debug(f"Getting info for collection '{self.collection_name}'")

            collection_info = self.client.get_collection(
                collection_name=self.collection_name
            )

            return {
                "name": collection_info.name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "config": str(collection_info.config),
            }

        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to get collection info: {str(e)}") from e

    def clear_collection(self) -> bool:
        """
        Clear all points from collection (keeps structure).

        Returns:
            True if cleared

        Raises:
            VectorDatabaseError: If operation fails
        """
        try:
            logger.warning(f"Clearing all points from '{self.collection_name}'")

            # Delete all points by deleting and recreating collection
            self.delete_collection()
            self.create_collection()

            logger.info(f"Successfully cleared collection '{self.collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to clear collection: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to clear collection: {str(e)}") from e

    def batch_search(
        self,
        query_vectors: List[List[float]],
        limit: int = 10,
    ) -> List[List[SearchResult]]:
        """
        Search for multiple query vectors.

        Args:
            query_vectors: List of query vectors
            limit: Results per query

        Returns:
            List of result lists

        Raises:
            VectorDatabaseError: If operation fails
        """
        results = []

        for idx, query_vector in enumerate(query_vectors):
            logger.debug(f"Batch search {idx + 1}/{len(query_vectors)}")
            search_results = self.search(query_vector, limit)
            results.append(search_results)

        return results
