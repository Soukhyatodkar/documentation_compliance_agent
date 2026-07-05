"""
Semantic retrieval engine for RAG pipeline.

Retrieves relevant guideline chunks from vector database
using semantic similarity and relevance scoring.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from src.data.models import GuidelineChunk
from src.core.exceptions import ValidationError

if TYPE_CHECKING:
    from src.vector_store.qdrant_client import QdrantVectorStore
    from src.vector_store.embeddings import EmbeddingGenerator


logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Single retrieval result."""

    chunk: GuidelineChunk
    score: float
    rank: int
    source_page: int

    def __repr__(self) -> str:
        return (
            f"RetrievalResult(chunk_id={self.chunk.chunk_id}, "
            f"score={self.score:.3f}, rank={self.rank})"
        )


class SemanticRetriever:
    """Semantic retrieval engine using embeddings and vector database."""

    def __init__(
        self,
        embedding_generator: "EmbeddingGenerator",
        vector_store: "QdrantVectorStore",
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize semantic retriever."""
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store
        
        # Configuration with defaults
        self.config = config or {}
        self.top_k = self.config.get("top_k", 10)
        self.relevance_threshold = self.config.get("relevance_threshold", 0.6)
        self.enable_deduplication = self.config.get("deduplication", True)
        self.max_context_length = self.config.get("max_context_length", 2000)
        
        # Query cache
        self._query_cache: Dict[str, List[RetrievalResult]] = {}
        self.cache_enabled = self.config.get("cache_enabled", True)
        
        logger.info("Initialized semantic retriever")

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        relevance_threshold: Optional[float] = None,
    ) -> List[RetrievalResult]:
        """Retrieve top-k relevant guideline chunks."""
        try:
            # Use provided values or defaults
            top_k = top_k or self.top_k
            relevance_threshold = relevance_threshold or self.relevance_threshold
            
            # Check cache
            cache_key = f"{query}_{top_k}_{relevance_threshold}"
            if self.cache_enabled and cache_key in self._query_cache:
                logger.debug(f"Cache hit for query: {query}")
                return self._query_cache[cache_key]
            
            # Generate embedding for query
            query_embedding = self.embedding_generator.embed_text(query)
            
            # Search vector database
            search_results = self.vector_store.search(
                query_vector=query_embedding,
                limit=top_k * 2,  # Get extra results for filtering
                score_threshold=relevance_threshold,
            )
            
            # Convert results to RetrievalResult objects
            results = []
            for rank, result in enumerate(search_results):
                try:
                    chunk = GuidelineChunk(**result.payload)
                    retrieval_result = RetrievalResult(
                        chunk=chunk,
                        score=result.score,
                        rank=rank + 1,
                        source_page=chunk.page_num,
                    )
                    results.append(retrieval_result)
                except Exception as e:
                    logger.warning(f"Failed to parse result: {e}")
                    continue
            
            # Apply deduplication if enabled
            if self.enable_deduplication:
                results = self._deduplicate_results(results)
            
            # Truncate to top_k
            results = results[:top_k]
            
            # Cache results
            if self.cache_enabled:
                self._query_cache[cache_key] = results
            
            logger.info(
                f"Retrieved {len(results)} chunks for query: "
                f"{query[:50]}... (threshold: {relevance_threshold})"
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Retrieval failed for query '{query}': {e}")
            raise

    def retrieve_by_component(
        self,
        component_text: str,
        component_type: str = "unknown",
        top_k: Optional[int] = None,
        context_text: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """Retrieve guideline chunks relevant to web component."""
        try:
            # Build query from component
            query_parts = [component_text]
            
            # Add component type for better context
            if component_type != "unknown":
                query_parts.append(f"Component type: {component_type}")
            
            # Add surrounding context if provided
            if context_text:
                query_parts.append(f"Context: {context_text[:100]}")
            
            query = " ".join(query_parts)
            
            # Retrieve relevant chunks
            results = self.retrieve(query, top_k=top_k)
            
            logger.debug(
                f"Retrieved {len(results)} chunks for component: "
                f"{component_text[:30]}... (type: {component_type})"
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Component retrieval failed: {e}")
            raise

    def multi_query_retrieve(
        self,
        query: str,
        expansion_queries: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """Retrieve using multiple query variations for better recall."""
        try:
            top_k = top_k or self.top_k
            all_results: Dict[str, RetrievalResult] = {}
            
            # Original query
            queries = [query]
            
            # Add expansion queries if provided
            if expansion_queries:
                queries.extend(expansion_queries)
            
            # Retrieve for each query
            for q in queries:
                try:
                    results = self.retrieve(q, top_k=top_k)
                    for result in results:
                        chunk_id = result.chunk.chunk_id
                        # Keep best score for duplicate chunks
                        if (chunk_id not in all_results or 
                            result.score > all_results[chunk_id].score):
                            all_results[chunk_id] = result
                except Exception as e:
                    logger.warning(f"Failed to retrieve for query '{q}': {e}")
            
            # Sort by score and assign ranks
            sorted_results = sorted(
                all_results.values(),
                key=lambda x: x.score,
                reverse=True,
            )
            
            # Re-rank
            for i, result in enumerate(sorted_results):
                result.rank = i + 1
            
            logger.info(
                f"Multi-query retrieval found {len(sorted_results)} unique chunks "
                f"(original query + {len(expansion_queries or [])} expansions)"
            )
            
            return sorted_results[:top_k]
        
        except Exception as e:
            logger.error(f"Multi-query retrieval failed: {e}")
            raise

    def retrieve_by_section(
        self,
        section: str,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """Retrieve chunks from specific guideline section."""
        try:
            # Add section context to query
            enhanced_query = f"Section: {section}. {query}"
            
            # Retrieve
            results = self.retrieve(enhanced_query, top_k=top_k)
            
            logger.debug(f"Retrieved {len(results)} chunks from section: {section}")
            
            return results
        
        except Exception as e:
            logger.error(f"Section retrieval failed: {e}")
            raise

    def batch_retrieve(
        self,
        queries: List[str],
        top_k: Optional[int] = None,
    ) -> Dict[str, List[RetrievalResult]]:
        """Retrieve for multiple queries."""
        try:
            results = {}
            
            for query in queries:
                try:
                    results[query] = self.retrieve(query, top_k=top_k)
                except Exception as e:
                    logger.warning(f"Failed to retrieve for query '{query}': {e}")
                    results[query] = []
            
            logger.info(f"Batch retrieval completed for {len(queries)} queries")
            
            return results
        
        except Exception as e:
            logger.error(f"Batch retrieval failed: {e}")
            raise

    def get_similar_chunks(
        self,
        chunk_id: str,
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """Find chunks similar to a given chunk."""
        try:
            # Find the chunk in vector store
            # This would require searching for the chunk ID
            # For now, retrieve general similar content
            
            logger.debug(f"Finding similar chunks for: {chunk_id}")
            
            # Would need to get the chunk's embedding and search for similar
            # This is a placeholder for future enhancement
            
            return []
        
        except Exception as e:
            logger.error(f"Similar chunks retrieval failed: {e}")
            raise

    def retrieve_by_page_range(
        self,
        query: str,
        start_page: int,
        end_page: int,
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """Retrieve chunks from specific page range."""
        try:
            top_k = top_k or self.top_k
            
            # Retrieve all relevant chunks
            all_results = self.retrieve(query, top_k=top_k * 3)
            
            # Filter by page range
            filtered_results = [
                r for r in all_results
                if start_page <= r.source_page <= end_page
            ]
            
            # Re-rank and truncate
            for i, result in enumerate(filtered_results):
                result.rank = i + 1
            
            logger.debug(
                f"Retrieved {len(filtered_results)} chunks from pages "
                f"{start_page}-{end_page}"
            )
            
            return filtered_results[:top_k]
        
        except Exception as e:
            logger.error(f"Page range retrieval failed: {e}")
            raise

    def clear_cache(self) -> None:
        """Clear query result cache."""
        cache_size = len(self._query_cache)
        self._query_cache.clear()
        logger.info(f"Cleared {cache_size} cached queries")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_queries": len(self._query_cache),
            "cache_enabled": self.cache_enabled,
            "top_k": self.top_k,
            "relevance_threshold": self.relevance_threshold,
            "deduplication_enabled": self.enable_deduplication,
        }

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            "cache_size": len(self._query_cache),
            "configuration": {
                "top_k": self.top_k,
                "relevance_threshold": self.relevance_threshold,
                "deduplication": self.enable_deduplication,
                "cache_enabled": self.cache_enabled,
                "max_context_length": self.max_context_length,
            },
        }

    def _deduplicate_results(
        self,
        results: List[RetrievalResult],
    ) -> List[RetrievalResult]:
        """Remove duplicate chunks keeping highest scoring."""
        seen_chunks: Dict[str, RetrievalResult] = {}
        
        for result in results:
            chunk_id = result.chunk.chunk_id
            if (chunk_id not in seen_chunks or 
                result.score > seen_chunks[chunk_id].score):
                seen_chunks[chunk_id] = result
        
        # Re-rank deduplicated results
        dedup_results = sorted(
            seen_chunks.values(),
            key=lambda x: x.score,
            reverse=True,
        )
        
        for i, result in enumerate(dedup_results):
            result.rank = i + 1
        
        logger.debug(
            f"Deduplicated results: {len(results)} -> {len(dedup_results)}"
        )
        
        return dedup_results


class RetrievalEvaluator:
    """Evaluate retrieval quality."""

    @staticmethod
    def evaluate_coverage(
        results: List[RetrievalResult],
        required_sections: List[str],
    ) -> Dict[str, Any]:
        """Evaluate coverage of required sections."""
        sections_covered = set()
        
        for result in results:
            if result.chunk.section:
                sections_covered.add(result.chunk.section)
        
        missing_sections = set(required_sections) - sections_covered
        coverage_pct = (
            (len(sections_covered) / len(required_sections) * 100)
            if required_sections
            else 0
        )
        
        return {
            "sections_covered": len(sections_covered),
            "sections_required": len(required_sections),
            "coverage_percentage": coverage_pct,
            "missing_sections": list(missing_sections),
        }

    @staticmethod
    def evaluate_quality(
        results: List[RetrievalResult],
        avg_score_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """Evaluate retrieval quality."""
        if not results:
            return {
                "count": 0,
                "average_score": 0.0,
                "min_score": 0.0,
                "max_score": 0.0,
                "quality_good": False,
            }
        
        scores = [r.score for r in results]
        avg_score = sum(scores) / len(scores)
        
        return {
            "count": len(results),
            "average_score": avg_score,
            "min_score": min(scores),
            "max_score": max(scores),
            "quality_good": avg_score >= avg_score_threshold,
        }

    @staticmethod
    def evaluate_diversity(
        results: List[RetrievalResult],
    ) -> Dict[str, Any]:
        """Evaluate diversity of retrieved chunks."""
        sections = set()
        pages = set()
        
        for result in results:
            if result.chunk.section:
                sections.add(result.chunk.section)
            pages.add(result.source_page)
        
        return {
            "unique_sections": len(sections),
            "unique_pages": len(pages),
            "total_results": len(results),
            "diversity_score": (len(sections) + len(pages)) / (len(results) * 2)
            if results
            else 0,
        }
