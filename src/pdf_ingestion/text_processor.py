"""
Text processing and cleaning for PDF content.

Normalizes, cleans, and prepares text for chunking and embedding.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class TextProcessor:
    """Process and clean text content."""

    # Common patterns to clean
    WHITESPACE_PATTERN = re.compile(r"\s+")
    NEWLINE_PATTERN = re.compile(r"\n{2,}")
    PAGE_BREAK_PATTERN = re.compile(r"(\x0c|\n\s*Page \d+)")
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    URL_PATTERN = re.compile(r"https?://[^\s\)]+")

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text by removing artifacts and normalizing whitespace.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove page breaks and page numbers
        text = TextProcessor.PAGE_BREAK_PATTERN.sub("\n", text)

        # Normalize whitespace
        text = TextProcessor.WHITESPACE_PATTERN.sub(" ", text)

        # Clean multiple newlines
        text = TextProcessor.NEWLINE_PATTERN.sub("\n\n", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    @staticmethod
    def extract_sentences(text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitting on period, question mark, exclamation
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def extract_paragraphs(text: str) -> List[str]:
        """
        Extract paragraphs from text.

        Args:
            text: Text to process

        Returns:
            List of paragraphs
        """
        # Split on double newlines
        paragraphs = text.split("\n\n")
        return [p.strip() for p in paragraphs if p.strip()]

    @staticmethod
    def detect_headings(text: str) -> Dict[str, List[str]]:
        """
        Detect potential headings based on formatting patterns.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with detected heading levels
        """
        headings = {"h1": [], "h2": [], "h3": []}

        lines = text.split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Detect based on patterns
            if all(c in "=#- " for c in stripped) and len(stripped) > 3:
                # Markdown-style heading
                if stripped.startswith("# "):
                    headings["h1"].append(stripped[2:].strip())
                elif stripped.startswith("## "):
                    headings["h2"].append(stripped[3:].strip())
                elif stripped.startswith("### "):
                    headings["h3"].append(stripped[4:].strip())

            # Detect all-caps lines as potential headings
            elif (
                len(stripped) < 100
                and stripped.isupper()
                and len(stripped.split()) < 10
            ):
                headings["h1"].append(stripped)

        return headings

    @staticmethod
    def remove_special_characters(text: str, keep_punctuation: bool = True) -> str:
        """
        Remove special characters from text.

        Args:
            text: Text to clean
            keep_punctuation: Keep punctuation marks

        Returns:
            Cleaned text
        """
        if keep_punctuation:
            # Keep alphanumeric, spaces, and common punctuation
            pattern = r"[^a-zA-Z0-9\s\.\,\!\?\;\:\-\(\)\"\'\n]"
        else:
            # Keep only alphanumeric and spaces
            pattern = r"[^a-zA-Z0-9\s\n]"

        return re.sub(pattern, "", text)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Normalize all whitespace to single spaces.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Replace tabs with spaces
        text = text.replace("\t", " ")

        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)

        # Clean up newlines (max 2)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text

    @staticmethod
    def extract_metadata(text: str) -> Dict[str, Any]:
        """
        Extract metadata from text (emails, URLs, etc.).

        Args:
            text: Text to analyze

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            "emails": list(set(TextProcessor.EMAIL_PATTERN.findall(text))),
            "urls": list(set(TextProcessor.URL_PATTERN.findall(text))),
            "word_count": len(text.split()),
            "char_count": len(text),
            "line_count": len(text.split("\n")),
        }

        return metadata

    @staticmethod
    def process_text(text: str, clean: bool = True, normalize: bool = True) -> str:
        """
        Complete text processing pipeline.

        Args:
            text: Text to process
            clean: Apply cleaning
            normalize: Apply normalization

        Returns:
            Processed text
        """
        if not text:
            return ""

        if clean:
            text = TextProcessor.clean_text(text)

        if normalize:
            text = TextProcessor.normalize_whitespace(text)

        return text
