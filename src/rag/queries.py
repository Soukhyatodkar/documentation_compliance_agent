"""
Query processing and expansion for RAG pipeline.

Processes component text into effective retrieval queries.
"""

import logging
import re
from typing import List, Optional, Dict, Any, Set
from collections import Counter

from src.data.models import WebComponent, ComponentType


logger = logging.getLogger(__name__)


class QueryProcessor:
    """Process and normalize queries for retrieval."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize query processor."""
        self.config = config or {}
        self.min_query_length = self.config.get("min_query_length", 3)
        self.max_query_length = self.config.get("max_query_length", 200)
        self.lowercase_queries = self.config.get("lowercase_queries", True)
        
        # Stop words to filter
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "up", "about",
            "is", "are", "was", "were", "be", "being", "have", "has",
            "had", "do", "does", "did", "will", "would", "could", "should",
        }
        
        logger.info("Initialized query processor")

    def process_component(self, component: WebComponent) -> str:
        """Process web component into query."""
        try:
            query_parts = []
            
            # Add component type
            query_parts.append(component.component_type.value)
            
            # Add actual text
            if component.actual_text:
                query_parts.append(component.actual_text)
            
            # Add HTML class/id hints
            if component.attributes:
                query_parts.extend(component.attributes.values())
            
            # Combine and clean
            query = " ".join(query_parts)
            query = self.normalize_query(query)
            
            logger.debug(f"Processed component query: {query[:50]}...")
            
            return query
        
        except Exception as e:
            logger.error(f"Failed to process component: {e}")
            raise

    def process_text(self, text: str) -> str:
        """Process raw text into query."""
        try:
            # Clean text
            text = text.strip()
            
            # Remove extra whitespace
            text = re.sub(r"\s+", " ", text)
            
            # Truncate if too long
            if len(text) > self.max_query_length:
                text = text[:self.max_query_length].rsplit(" ", 1)[0]
            
            # Normalize
            query = self.normalize_query(text)
            
            return query
        
        except Exception as e:
            logger.error(f"Failed to process text: {e}")
            raise

    def normalize_query(self, query: str) -> str:
        """Normalize query string."""
        try:
            # Remove special characters but keep meaningful ones
            query = re.sub(r"[^a-zA-Z0-9\s\-_]", "", query)
            
            # Lowercase if configured
            if self.lowercase_queries:
                query = query.lower()
            
            # Remove extra whitespace
            query = " ".join(query.split())
            
            # Filter stop words
            tokens = query.split()
            tokens = [t for t in tokens if t not in self.stop_words]
            query = " ".join(tokens)
            
            # Ensure minimum length
            if len(query) < self.min_query_length:
                query = ""
            
            return query
        
        except Exception as e:
            logger.error(f"Failed to normalize query: {e}")
            return query

    def extract_keyphrases(self, text: str, top_k: int = 5) -> List[str]:
        """Extract key phrases from text."""
        try:
            # Split into words
            words = text.lower().split()
            
            # Remove stop words
            words = [w for w in words if w not in self.stop_words and len(w) > 2]
            
            # Count frequency
            freq = Counter(words)
            
            # Get top keyphrases
            keyphrases = [word for word, _ in freq.most_common(top_k)]
            
            logger.debug(f"Extracted keyphrases: {keyphrases}")
            
            return keyphrases
        
        except Exception as e:
            logger.error(f"Failed to extract keyphrases: {e}")
            return []

    def split_into_subqueries(
        self,
        query: str,
        max_subqueries: int = 3,
    ) -> List[str]:
        """Split query into subqueries."""
        try:
            subqueries = [query]  # Include original
            
            # Split by common delimiters
            for delimiter in [" and ", " or ", ","]:
                if delimiter in query:
                    parts = query.split(delimiter)
                    for part in parts:
                        part = part.strip()
                        if len(part) >= self.min_query_length:
                            subqueries.append(part)
                    break
            
            # Remove duplicates and limit
            subqueries = list(set(subqueries))[:max_subqueries]
            
            logger.debug(f"Split into {len(subqueries)} subqueries")
            
            return subqueries
        
        except Exception as e:
            logger.error(f"Failed to split query: {e}")
            return [query]


class QueryExpander:
    """Expand queries with synonyms and related terms."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize query expander."""
        self.config = config or {}
        
        # Synonym mappings
        self.synonyms: Dict[str, List[str]] = {
            "login": ["authentication", "signin", "sign in", "logon"],
            "password": ["credentials", "passphrase", "secret"],
            "submit": ["send", "post", "upload", "confirm"],
            "button": ["link", "control", "element", "action"],
            "form": ["input", "field", "entry", "form field"],
            "error": ["alert", "warning", "message", "notification"],
            "success": ["valid", "complete", "done", "finished"],
            "required": ["mandatory", "necessary", "needed", "essential"],
            "optional": ["optional", "additional", "extra"],
        }
        
        logger.info("Initialized query expander")

    def expand_query(
        self,
        query: str,
        max_expansions: int = 3,
    ) -> List[str]:
        """Expand query with synonyms and variations."""
        try:
            expansions = [query]
            
            # Find keywords with synonyms
            query_lower = query.lower()
            
            for keyword, synonyms in self.synonyms.items():
                if keyword in query_lower:
                    for synonym in synonyms[:max_expansions]:
                        expanded = query_lower.replace(keyword, synonym)
                        if expanded not in expansions:
                            expansions.append(expanded)
            
            logger.debug(f"Generated {len(expansions)} query expansions")
            
            return expansions[:max_expansions + 1]
        
        except Exception as e:
            logger.error(f"Failed to expand query: {e}")
            return [query]

    def generate_variations(
        self,
        component: WebComponent,
        num_variations: int = 3,
    ) -> List[str]:
        """Generate query variations for component."""
        try:
            variations = []
            
            # Variation 1: Component type + text
            if component.actual_text:
                comp_type = component.component_type.value if hasattr(component.component_type, 'value') else str(component.component_type)
                v1 = f"{comp_type} {component.actual_text}"
                variations.append(v1)
            
            # Variation 2: Just text
            if component.actual_text:
                variations.append(component.actual_text)
            
            # Variation 3: Component type + context
            comp_type = component.component_type.value if hasattr(component.component_type, 'value') else str(component.component_type)
            v3 = f"{comp_type} requirements"
            variations.append(v3)
            
            # Trim to requested number
            variations = variations[:num_variations]
            
            logger.debug(f"Generated {len(variations)} variations for component")
            
            return variations
        
        except Exception as e:
            logger.error(f"Failed to generate variations: {e}")
            return []


class QueryCache:
    """Cache query results for efficiency."""

    def __init__(self, max_cache_size: int = 1000):
        """Initialize query cache."""
        self.cache: Dict[str, List[Any]] = {}
        self.max_cache_size = max_cache_size
        self.hits = 0
        self.misses = 0
        
        logger.info(f"Initialized query cache (max size: {max_cache_size})")

    def get(self, query: str) -> Optional[List[Any]]:
        """Get cached result."""
        if query in self.cache:
            self.hits += 1
            logger.debug(f"Cache hit for query: {query[:30]}...")
            return self.cache[query]
        
        self.misses += 1
        return None

    def put(self, query: str, results: List[Any]) -> None:
        """Store result in cache."""
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[query] = results
        logger.debug(f"Cached query: {query[:30]}...")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "cached_queries": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percentage": hit_rate,
        }

    def clear(self) -> None:
        """Clear cache."""
        size = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared cache ({size} entries)")


class QueryAnalyzer:
    """Analyze query quality and relevance."""

    @staticmethod
    def analyze_query(query: str) -> Dict[str, Any]:
        """Analyze query characteristics."""
        return {
            "length": len(query),
            "word_count": len(query.split()),
            "has_keywords": any(
                keyword in query.lower()
                for keyword in ["required", "must", "should", "cannot"]
            ),
            "has_negation": "not" in query.lower() or "no" in query.lower(),
            "specificity": len(set(query.split())) / len(query.split())
            if query.split()
            else 0,
        }

    @staticmethod
    def compare_queries(query1: str, query2: str) -> float:
        """Calculate similarity between two queries (0-1)."""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def deduplicate_queries(queries: List[str], threshold: float = 0.8) -> List[str]:
        """Remove duplicate or very similar queries."""
        unique_queries = []
        
        for query in queries:
            is_duplicate = False
            
            for existing in unique_queries:
                similarity = QueryAnalyzer.compare_queries(query, existing)
                if similarity >= threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_queries.append(query)
        
        return unique_queries
