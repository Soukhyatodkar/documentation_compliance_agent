"""
Semantic text chunking for PDF content.

Splits text into meaningful chunks while preserving context,
headings, and metadata.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a single text chunk."""

    chunk_id: str
    text: str
    page_num: int
    section: Optional[str] = None
    heading: Optional[str] = None
    position: int = 0  # Position in original text
    start_char: int = 0
    end_char: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate chunk_id if not provided."""
        if not self.chunk_id:
            # Generate deterministic hash-based ID
            hash_input = f"{self.page_num}_{self.position}_{self.text[:50]}"
            self.chunk_id = hashlib.md5(hash_input.encode()).hexdigest()[:12]


class ChunkGenerator:
    """Generate semantic chunks from text."""

    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
        overlap: int = 100,
        preserve_headings: bool = True,
    ):
        """
        Initialize chunk generator.

        Args:
            min_chunk_size: Minimum characters per chunk
            max_chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks
            preserve_headings: Keep headings with chunks
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.preserve_headings = preserve_headings

        logger.info(
            f"Initialized ChunkGenerator: min={min_chunk_size}, "
            f"max={max_chunk_size}, overlap={overlap}"
        )

    def chunk_text(
        self,
        text: str,
        page_num: int = 1,
        heading: Optional[str] = None,
        section: Optional[str] = None,
    ) -> List[TextChunk]:
        """
        Split text into semantic chunks.

        Args:
            text: Text to chunk
            page_num: Page number
            heading: Section heading
            section: Section identifier

        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            logger.warning(f"Empty text provided for page {page_num}")
            return []

        # Clean text
        text = text.strip()

        # Split into sentences first
        sentences = self._split_sentences(text)

        if not sentences:
            logger.warning(f"No sentences extracted from page {page_num}")
            return []

        # Combine sentences into chunks
        chunks = self._combine_into_chunks(sentences, page_num, heading, section, text)

        logger.debug(f"Generated {len(chunks)} chunks from page {page_num}")
        return chunks

    def chunk_pages(
        self, pages: List[Dict[str, Any]]
    ) -> List[TextChunk]:
        """
        Chunk multiple pages.

        Args:
            pages: List of page dictionaries with 'text', 'page_num', 'heading', 'section'

        Returns:
            List of TextChunk objects from all pages
        """
        all_chunks = []

        for page in pages:
            text = page.get("text", "")
            page_num = page.get("page_num", 1)
            heading = page.get("heading")
            section = page.get("section")

            chunks = self.chunk_text(text, page_num, heading, section)
            all_chunks.extend(chunks)

        logger.info(f"Generated {len(all_chunks)} total chunks from {len(pages)} pages")
        return all_chunks

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        import re

        # Split on sentence boundaries
        sentence_endings = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
        sentences = sentence_endings.split(text)

        return [s.strip() for s in sentences if s.strip()]

    def _combine_into_chunks(
        self,
        sentences: List[str],
        page_num: int,
        heading: Optional[str],
        section: Optional[str],
        original_text: str,
    ) -> List[TextChunk]:
        """
        Combine sentences into chunks of target size.

        Args:
            sentences: List of sentences
            page_num: Page number
            heading: Section heading
            section: Section identifier
            original_text: Original text for position tracking

        Returns:
            List of TextChunk objects
        """
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_start_pos = 0
        chunk_start_char = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            # Check if adding this sentence exceeds max chunk size
            if current_size + sentence_size > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunk_end_char = chunk_start_char + len(chunk_text)

                chunk = TextChunk(
                    chunk_id="",  # Will be generated
                    text=chunk_text,
                    page_num=page_num,
                    section=section,
                    heading=heading if self.preserve_headings else None,
                    position=chunk_start_pos,
                    start_char=chunk_start_char,
                    end_char=chunk_end_char,
                    metadata={
                        "sentence_count": len(current_chunk),
                        "character_count": len(chunk_text),
                    },
                )

                chunks.append(chunk)

                # Start new chunk with overlap
                if self.overlap > 0 and current_chunk:
                    # Calculate overlap sentences
                    overlap_text = chunk_text[-self.overlap :]
                    current_chunk = [overlap_text] if overlap_text else []
                    current_size = len(" ".join(current_chunk))
                    chunk_start_char = chunk_end_char - self.overlap
                else:
                    current_chunk = []
                    current_size = 0
                    chunk_start_char = chunk_end_char

                chunk_start_pos += 1

            current_chunk.append(sentence)
            current_size += sentence_size + 1  # +1 for space

        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_end_char = chunk_start_char + len(chunk_text)

            chunk = TextChunk(
                chunk_id="",
                text=chunk_text,
                page_num=page_num,
                section=section,
                heading=heading if self.preserve_headings else None,
                position=chunk_start_pos,
                start_char=chunk_start_char,
                end_char=chunk_end_char,
                metadata={
                    "sentence_count": len(current_chunk),
                    "character_count": len(chunk_text),
                },
            )

            chunks.append(chunk)

        # Filter out chunks that are too small
        chunks = [c for c in chunks if len(c.text) >= self.min_chunk_size]

        return chunks

    def validate_chunks(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """
        Validate chunk quality and return statistics.

        Args:
            chunks: List of chunks to validate

        Returns:
            Dictionary with validation statistics
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_size": 0,
                "min_size": 0,
                "max_size": 0,
                "issues": ["No chunks provided"],
            }

        sizes = [len(c.text) for c in chunks]
        issues = []

        # Check for size violations
        for chunk in chunks:
            size = len(chunk.text)
            if size < self.min_chunk_size:
                issues.append(f"Chunk {chunk.chunk_id} below minimum size ({size})")
            if size > self.max_chunk_size:
                issues.append(f"Chunk {chunk.chunk_id} above maximum size ({size})")

        stats = {
            "total_chunks": len(chunks),
            "avg_size": sum(sizes) / len(sizes),
            "min_size": min(sizes),
            "max_size": max(sizes),
            "total_characters": sum(sizes),
            "issues": issues,
        }

        if issues:
            logger.warning(f"Chunk validation found {len(issues)} issues")

        return stats
