"""
PDF text extraction and parsing.

Extracts text content from PDF files while preserving structure,
headings, and metadata.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import pypdf
import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class PDFPage:
    """Represents a single page from a PDF."""

    page_num: int
    text: str
    heading: Optional[str] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PDFContent:
    """Complete PDF content."""

    file_path: str
    total_pages: int
    pages: List[PDFPage]
    document_title: Optional[str] = None
    document_metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.document_metadata is None:
            self.document_metadata = {}


class PDFReader:
    """Extract text content from PDF files."""

    def __init__(self, pdf_path: str):
        """
        Initialize PDF reader.

        Args:
            pdf_path: Path to PDF file

        Raises:
            FileNotFoundError: If PDF not found
        """
        self.pdf_path = Path(pdf_path)

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if not self.pdf_path.suffix.lower() == ".pdf":
            raise ValueError(f"File is not a PDF: {pdf_path}")

        logger.info(f"Initialized PDFReader for {pdf_path}")

    def extract_text(self) -> PDFContent:
        """
        Extract all text from PDF.

        Returns:
            PDFContent object with all pages

        Raises:
            Exception: If extraction fails
        """
        try:
            logger.info(f"Extracting text from {self.pdf_path}")

            # Try using pdfplumber for better extraction
            pages = self._extract_with_pdfplumber()

            # Get document metadata
            doc_metadata = self._get_metadata()

            pdf_content = PDFContent(
                file_path=str(self.pdf_path),
                total_pages=len(pages),
                pages=pages,
                document_title=doc_metadata.get("title"),
                document_metadata=doc_metadata,
            )

            logger.info(f"Successfully extracted {len(pages)} pages from PDF")
            return pdf_content

        except Exception as e:
            logger.error(f"Failed to extract PDF: {str(e)}", exc_info=True)
            raise

    def _extract_with_pdfplumber(self) -> List[PDFPage]:
        """
        Extract text using pdfplumber (preserves structure better).

        Returns:
            List of PDFPage objects
        """
        pages = []

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    text = page.extract_text()

                    if not text or not text.strip():
                        logger.warning(f"Page {page_num} has no text content")
                        continue

                    # Try to detect heading (first non-empty line)
                    lines = text.strip().split("\n")
                    heading = None
                    if lines:
                        potential_heading = lines[0].strip()
                        if len(potential_heading) < 100:  # Headings typically short
                            heading = potential_heading

                    page_obj = PDFPage(
                        page_num=page_num,
                        text=text,
                        heading=heading,
                        metadata={
                            "width": page.width,
                            "height": page.height,
                        },
                    )

                    pages.append(page_obj)

            return pages

        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {str(e)}, falling back to pypdf")
            return self._extract_with_pypdf()

    def _extract_with_pypdf(self) -> List[PDFPage]:
        """
        Fallback extraction using pypdf.

        Returns:
            List of PDFPage objects
        """
        pages = []

        try:
            with open(self.pdf_path, "rb") as f:
                pdf_reader = pypdf.PdfReader(f)

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    # Extract text
                    text = page.extract_text()

                    if not text or not text.strip():
                        logger.warning(f"Page {page_num} has no text content")
                        continue

                    # Try to detect heading
                    lines = text.strip().split("\n")
                    heading = None
                    if lines:
                        potential_heading = lines[0].strip()
                        if len(potential_heading) < 100:
                            heading = potential_heading

                    page_obj = PDFPage(
                        page_num=page_num,
                        text=text,
                        heading=heading,
                        metadata={},
                    )

                    pages.append(page_obj)

            return pages

        except Exception as e:
            logger.error(f"pypdf extraction failed: {str(e)}", exc_info=True)
            raise

    def _get_metadata(self) -> Dict[str, Any]:
        """
        Get PDF document metadata.

        Returns:
            Dictionary with metadata
        """
        try:
            with open(self.pdf_path, "rb") as f:
                pdf_reader = pypdf.PdfReader(f)

                if pdf_reader.metadata:
                    return {
                        "title": pdf_reader.metadata.get("/Title", ""),
                        "author": pdf_reader.metadata.get("/Author", ""),
                        "subject": pdf_reader.metadata.get("/Subject", ""),
                        "creator": pdf_reader.metadata.get("/Creator", ""),
                        "producer": pdf_reader.metadata.get("/Producer", ""),
                        "creation_date": str(pdf_reader.metadata.get("/CreationDate", "")),
                    }

            return {}

        except Exception as e:
            logger.warning(f"Failed to extract metadata: {str(e)}")
            return {}

    def extract_tables(self) -> List[Dict[str, Any]]:
        """
        Extract tables from PDF.

        Returns:
            List of extracted tables

        Note:
            This requires pdfplumber and may not work for all PDFs.
        """
        tables = []

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    if page.tables:
                        for table in page.tables:
                            tables.append(
                                {
                                    "page": page_num,
                                    "data": table,
                                }
                            )

            logger.info(f"Extracted {len(tables)} tables from PDF")
            return tables

        except Exception as e:
            logger.warning(f"Failed to extract tables: {str(e)}")
            return []

    def get_page_count(self) -> int:
        """
        Get total number of pages in PDF.

        Returns:
            Page count
        """
        try:
            with open(self.pdf_path, "rb") as f:
                pdf_reader = pypdf.PdfReader(f)
                return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"Failed to get page count: {str(e)}")
            return 0
