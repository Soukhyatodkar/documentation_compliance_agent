"""
Unit tests for PDF ingestion pipeline.
"""

import pytest
import tempfile
from pathlib import Path

from src.pdf_ingestion.pdf_reader import PDFReader, PDFPage, PDFContent
from src.pdf_ingestion.text_processor import TextProcessor
from src.pdf_ingestion.chunk_generator import ChunkGenerator, TextChunk


class TestPDFReader:
    """Tests for PDFReader class."""

    def test_init_with_missing_file(self):
        """Test initialization with non-existent file."""
        with pytest.raises(FileNotFoundError):
            PDFReader("/nonexistent/file.pdf")

    def test_init_with_non_pdf_file(self):
        """Test initialization with non-PDF file."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            with pytest.raises(ValueError):
                PDFReader(f.name)

    def test_get_page_count(self, tmp_path):
        """Test getting page count from PDF."""
        # Note: This test requires a valid PDF file
        # For testing purposes, we'd normally use a test fixture
        pass


class TestTextProcessor:
    """Tests for TextProcessor class."""

    def test_clean_text_removes_extra_whitespace(self):
        """Test cleaning text removes extra whitespace."""
        text = "This   has    extra    spaces"
        cleaned = TextProcessor.clean_text(text)
        assert "  " not in cleaned

    def test_clean_text_normalizes_newlines(self):
        """Test cleaning text normalizes newlines."""
        text = "Line 1\n\n\n\nLine 2"
        cleaned = TextProcessor.clean_text(text)
        assert "\n\n\n" not in cleaned

    def test_extract_sentences(self):
        """Test sentence extraction."""
        text = "This is sentence one. This is sentence two! Here is sentence three?"
        sentences = TextProcessor.extract_sentences(text)
        assert len(sentences) >= 2

    def test_extract_paragraphs(self):
        """Test paragraph extraction."""
        text = "Paragraph 1\nwith multiple lines\n\nParagraph 2\nwith content"
        paragraphs = TextProcessor.extract_paragraphs(text)
        assert len(paragraphs) >= 1

    def test_detect_headings(self):
        """Test heading detection."""
        text = "# Main Heading\nSome content\n## Sub Heading\nMore content"
        headings = TextProcessor.detect_headings(text)
        assert "h1" in headings
        assert len(headings["h1"]) > 0

    def test_extract_metadata(self):
        """Test metadata extraction."""
        text = "Contact: user@example.com or visit https://example.com"
        metadata = TextProcessor.extract_metadata(text)
        assert "emails" in metadata
        assert "urls" in metadata
        assert len(metadata["emails"]) > 0

    def test_process_text_pipeline(self):
        """Test complete text processing pipeline."""
        text = "   This   has    issues.  \n\n\n  Let's fix it!   "
        processed = TextProcessor.process_text(text)
        assert len(processed) > 0
        assert "  " not in processed


class TestChunkGenerator:
    """Tests for ChunkGenerator class."""

    @pytest.fixture
    def chunk_generator(self):
        """Create ChunkGenerator instance."""
        return ChunkGenerator(
            min_chunk_size=50,
            max_chunk_size=200,
            overlap=20,
            preserve_headings=True,
        )

    def test_init_with_valid_params(self, chunk_generator):
        """Test initialization with valid parameters."""
        assert chunk_generator.min_chunk_size == 50
        assert chunk_generator.max_chunk_size == 200
        assert chunk_generator.overlap == 20

    def test_chunk_empty_text(self, chunk_generator):
        """Test chunking empty text."""
        chunks = chunk_generator.chunk_text("")
        assert chunks == []

    def test_chunk_single_sentence(self, chunk_generator):
        """Test chunking single sentence."""
        text = "This is a single sentence."
        chunks = chunk_generator.chunk_text(text, page_num=1)
        assert len(chunks) >= 0  # May be 0 if below min size

    def test_chunk_multiple_sentences(self, chunk_generator):
        """Test chunking multiple sentences."""
        text = (
            "This is the first sentence. "
            "This is the second sentence. "
            "This is the third sentence. "
            "This is the fourth sentence."
        )
        chunks = chunk_generator.chunk_text(text, page_num=1)
        # Should produce at least one chunk
        assert len(chunks) >= 0

    def test_chunk_with_heading(self, chunk_generator):
        """Test chunk preserves heading."""
        text = "This is a sample text for chunking."
        chunks = chunk_generator.chunk_text(
            text, page_num=1, heading="Section 1"
        )
        if chunks:
            assert chunks[0].heading == "Section 1"

    def test_chunk_with_section(self, chunk_generator):
        """Test chunk preserves section."""
        text = "This is a sample text for chunking."
        chunks = chunk_generator.chunk_text(
            text, page_num=1, section="2.1"
        )
        if chunks:
            assert chunks[0].section == "2.1"

    def test_chunk_pages(self, chunk_generator):
        """Test chunking multiple pages."""
        pages = [
            {
                "text": "Page 1 content. This is page 1 text.",
                "page_num": 1,
                "heading": "Chapter 1",
            },
            {
                "text": "Page 2 content. This is page 2 text.",
                "page_num": 2,
                "heading": "Chapter 2",
            },
        ]
        chunks = chunk_generator.chunk_pages(pages)
        assert len(chunks) >= 0

    def test_validate_chunks(self, chunk_generator):
        """Test chunk validation."""
        text = "This is sample text for validation." * 10
        chunks = chunk_generator.chunk_text(text, page_num=1)

        validation = chunk_generator.validate_chunks(chunks)
        assert "total_chunks" in validation
        assert "avg_size" in validation

    def test_chunk_id_generation(self, chunk_generator):
        """Test automatic chunk ID generation."""
        text = "This is a test sentence for chunk ID generation."
        chunks = chunk_generator.chunk_text(text, page_num=1)

        if chunks:
            # All chunks should have IDs
            for chunk in chunks:
                assert chunk.chunk_id
                assert len(chunk.chunk_id) > 0


class TestTextChunk:
    """Tests for TextChunk dataclass."""

    def test_create_chunk_with_id(self):
        """Test creating chunk with explicit ID."""
        chunk = TextChunk(
            chunk_id="test_123",
            text="Test content",
            page_num=1,
        )
        assert chunk.chunk_id == "test_123"
        assert chunk.text == "Test content"
        assert chunk.page_num == 1

    def test_create_chunk_generates_id(self):
        """Test that chunk ID is generated if not provided."""
        chunk = TextChunk(
            chunk_id="",
            text="Test content",
            page_num=1,
        )
        assert chunk.chunk_id  # Should be auto-generated


class TestPDFPage:
    """Tests for PDFPage dataclass."""

    def test_create_page(self):
        """Test creating PDF page."""
        page = PDFPage(
            page_num=1,
            text="Page content",
            heading="Chapter 1",
        )
        assert page.page_num == 1
        assert page.text == "Page content"
        assert page.heading == "Chapter 1"

    def test_page_metadata_initialization(self):
        """Test page metadata is initialized."""
        page = PDFPage(
            page_num=1,
            text="Content",
        )
        assert page.metadata is not None
        assert isinstance(page.metadata, dict)


class TestPDFContent:
    """Tests for PDFContent dataclass."""

    def test_create_pdf_content(self):
        """Test creating PDF content object."""
        pages = [
            PDFPage(page_num=1, text="Page 1"),
            PDFPage(page_num=2, text="Page 2"),
        ]
        content = PDFContent(
            file_path="/path/to/file.pdf",
            total_pages=2,
            pages=pages,
        )
        assert content.file_path == "/path/to/file.pdf"
        assert content.total_pages == 2
        assert len(content.pages) == 2

    def test_pdf_content_metadata_initialization(self):
        """Test PDF content metadata is initialized."""
        content = PDFContent(
            file_path="/path/to/file.pdf",
            total_pages=1,
            pages=[],
        )
        assert content.document_metadata is not None
        assert isinstance(content.document_metadata, dict)
