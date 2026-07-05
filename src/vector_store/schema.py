"""
Vector database schema and data models.

Defines the structure for storing chunks with embeddings in Qdrant.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


@dataclass
class ChunkPoint:
    """Point (document) to store in Qdrant."""

    # Point metadata
    point_id: int
    vector: List[float]

    # Chunk content
    text: str
    chunk_id: str

    # Source information
    page_num: int
    source_file: str
    
    # Context
    section: Optional[str] = None
    heading: Optional[str] = None
    
    # Position tracking
    position: int = 0
    start_char: int = 0
    end_char: int = 0
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """
        Convert to Qdrant payload (metadata).

        Returns:
            Dictionary suitable for Qdrant payload
        """
        return {
            "text": self.text,
            "chunk_id": self.chunk_id,
            "page_num": self.page_num,
            "source_file": self.source_file,
            "section": self.section,
            "heading": self.heading,
            "position": self.position,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    def to_qdrant_dict(self) -> Dict[str, Any]:
        """
        Convert to Qdrant point dictionary.

        Returns:
            Dictionary with id, vector, and payload
        """
        return {
            "id": self.point_id,
            "vector": self.vector,
            "payload": self.to_payload(),
        }


@dataclass
class SearchQuery:
    """Query for vector search."""

    query_vector: List[float]
    limit: int = 10
    score_threshold: Optional[float] = None
    filter_page: Optional[int] = None
    filter_section: Optional[str] = None
    filter_heading: Optional[str] = None


@dataclass
class SearchHit:
    """Result from vector search."""

    point_id: int
    score: float
    text: str
    chunk_id: str
    page_num: int
    source_file: str
    section: Optional[str] = None
    heading: Optional[str] = None
    position: int = 0
    start_char: int = 0
    end_char: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_qdrant_result(cls, result: Any) -> "SearchHit":
        """
        Create SearchHit from Qdrant search result.

        Args:
            result: Qdrant search result

        Returns:
            SearchHit instance
        """
        payload = result.payload

        return cls(
            point_id=result.id,
            score=result.score,
            text=payload.get("text", ""),
            chunk_id=payload.get("chunk_id", ""),
            page_num=payload.get("page_num", 0),
            source_file=payload.get("source_file", ""),
            section=payload.get("section"),
            heading=payload.get("heading"),
            position=payload.get("position", 0),
            start_char=payload.get("start_char", 0),
            end_char=payload.get("end_char", 0),
            metadata=payload.get("metadata", {}),
        )


class VectorStoreSchema:
    """Schema documentation for vector store."""

    # Collection structure
    COLLECTION_CONFIG = {
        "name": "guidelines",
        "vector_size": 1536,
        "distance_metric": "cosine",
        "description": "Semantic embeddings of guideline chunks",
    }

    # Payload schema (metadata stored with vectors)
    PAYLOAD_SCHEMA = {
        "text": "str - Full text of chunk",
        "chunk_id": "str - Unique chunk identifier",
        "page_num": "int - Source page number",
        "source_file": "str - Source file path",
        "section": "str (optional) - Section identifier",
        "heading": "str (optional) - Section heading",
        "position": "int - Chunk position in document",
        "start_char": "int - Starting character index",
        "end_char": "int - Ending character index",
        "created_at": "str - Creation timestamp (ISO format)",
        "updated_at": "str - Last update timestamp (ISO format)",
        "metadata": "dict - Additional metadata",
    }

    # Indexing strategy
    INDEXING_STRATEGY = {
        "dense_vectors": "All chunks indexed via cosine similarity",
        "metadata_filtering": "Optional filtering by page, section, heading",
        "similarity_threshold": "Configurable minimum similarity score",
    }

    @staticmethod
    def get_schema_json() -> str:
        """Get schema as JSON string."""
        return json.dumps(
            {
                "collection": VectorStoreSchema.COLLECTION_CONFIG,
                "payload_schema": VectorStoreSchema.PAYLOAD_SCHEMA,
                "indexing_strategy": VectorStoreSchema.INDEXING_STRATEGY,
            },
            indent=2,
        )
