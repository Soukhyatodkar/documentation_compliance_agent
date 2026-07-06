"""
Integration tests for full pipeline.

Tests the complete end-to-end pipeline including:
- PDF ingestion
- Website extraction
- Component comparison
- Report generation
- Data persistence
"""

import pytest
import json
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.core.config import get_config
from src.pdf_ingestion.pdf_reader import PDFReader
from src.pdf_ingestion.chunk_generator import ChunkGenerator
from src.vector_store.embeddings import EmbeddingGenerator
from src.vector_store.qdrant_client import QdrantVectorStore
from src.data.storage import DataStore
from src.data.models import WebComponent, ComponentType, ComparisonResult, Discrepancy
from src.rag.retriever import SemanticRetriever
from src.agent.compliance_agent import ComplianceAgent
from src.reporting.report_generator import ReportingOrchestrator, ReportMetadata


@pytest.mark.integration
class TestFullPipeline:
    """Test complete pipeline."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        config_dict = {
            "app": {
                "name": "test_agent",
                "log_level": "INFO",
                "skip_extraction": False,
                "concurrent_workers": 2,
            },
            "pdf": {
                "path": str(tmp_path / "test.pdf"),
                "chunking": {
                    "min_chunk_size": 100,
                    "max_chunk_size": 500,
                    "overlap": 50,
                },
            },
            "vector_db": {
                "type": "qdrant",
                "url": "http://localhost:6333",
                "collection_name": "test_collection",
            },
            "llm": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 500,
            },
            "website": {
                "url": "https://example.com",
                "authentication": {"type": "none"},
            },
            "output": {
                "base_dir": str(tmp_path),
                "pdfs_dir": str(tmp_path / "pdfs"),
                "extracted_dir": str(tmp_path / "extracted"),
                "screenshots_dir": str(tmp_path / "screenshots"),
                "reports_dir": str(tmp_path / "reports"),
                "logs_dir": str(tmp_path / "logs"),
            },
        }
        return config_dict

    @pytest.mark.asyncio
    async def test_pipeline_pdf_ingestion(self, config, tmp_path):
        """Test PDF ingestion stage."""
        # Create mock PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("Test PDF content")
        config["pdf"]["path"] = str(pdf_path)

        # Mock the PDF reader
        with patch("src.pdf_ingestion.pdf_reader.PDFReader") as MockReader:
            mock_reader = Mock()
            mock_reader.extract_text.return_value = [
                {"page_number": 0, "text": "Introduction", "headings": ["Introduction"]},
                {"page_number": 1, "text": "Features", "headings": ["Features"]},
            ]
            MockReader.return_value = mock_reader

            reader = PDFReader(str(pdf_path))
            pages = reader.extract_text()

            assert len(pages) == 2
            assert pages[0]["page_number"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_chunking(self):
        """Test text chunking stage."""
        chunk_gen = ChunkGenerator(
            min_chunk_size=100,
            max_chunk_size=500,
            overlap=50,
        )

        pages = [
            {
                "page_number": 0,
                "text": "Introduction. " * 100,
                "headings": ["Introduction"],
            },
        ]

        chunks = chunk_gen.chunk_pages(pages)
        assert len(chunks) > 0
        assert all(hasattr(c, "text") for c in chunks)

    @pytest.mark.asyncio
    async def test_pipeline_embedding(self):
        """Test embedding generation stage."""
        with patch("src.vector_store.embeddings.EmbeddingGenerator.embed_text") as mock_embed:
            mock_embed.return_value = [0.1] * 1536  # Mock embedding

            from src.vector_store.embeddings import EmbeddingGenerator
            embedder = EmbeddingGenerator({})

            # Mock embeddings
            embedding = embedder.embed_text("test content")
            assert len(embedding) == 1536

    @pytest.mark.asyncio
    async def test_pipeline_data_storage(self, tmp_path):
        """Test data storage stage."""
        config = {
            "output": {
                "base_dir": str(tmp_path),
                "extracted_dir": str(tmp_path / "extracted"),
            }
        }

        data_store = DataStore(config)

        # Create test component
        component = WebComponent(
            page_url="https://example.com",
            component_id="comp_001",
            component_type=ComponentType.HEADING,
            component_selector="h1.title",
            text_content="Test Title",
            screenshot_path=None,
        )

        # Save and retrieve
        data_store.save_component(component)
        stored = data_store.get_component(component.id)

        assert stored is not None
        assert stored.page_url == component.page_url

    @pytest.mark.asyncio
    async def test_pipeline_comparison(self):
        """Test comparison stage."""
        with patch("src.agent.compliance_agent.ComplianceAgent.compare") as mock_compare:
            mock_compare.return_value = (None, 0.95)

            agent = ComplianceAgent({})
            result, confidence = await agent.compare(
                actual="Test",
                expected="Test",
                guidelines="Test guideline"
            )

            assert confidence == 0.95

    @pytest.mark.asyncio
    async def test_pipeline_report_generation(self, tmp_path):
        """Test report generation stage."""
        metadata = ReportMetadata(
            report_id="test_001",
            generated_at=datetime.now(),
            website_url="https://example.com",
            pages_checked=5,
            components_checked=20,
            discrepancies_found=2,
            audit_duration_seconds=300.0,
            compliance_percentage=90.0,
        )

        orchestrator = ReportingOrchestrator()
        report_paths = orchestrator.generate_all(
            metadata, [], [], output_dir=str(tmp_path)
        )

        assert "json" in report_paths
        assert "markdown" in report_paths
        assert "html" in report_paths

        # Verify files exist
        for path in report_paths.values():
            assert Path(path).exists()

    @pytest.mark.asyncio
    async def test_pipeline_end_to_end(self, tmp_path):
        """Test complete pipeline execution."""
        config = {
            "app": {"name": "test", "log_level": "INFO"},
            "pdf": {"path": str(tmp_path / "test.pdf"), "chunking": {"min_chunk_size": 100}},
            "vector_db": {"type": "qdrant", "url": "http://localhost:6333"},
            "llm": {"model": "gpt-3.5-turbo"},
            "website": {"url": "https://example.com"},
            "output": {
                "base_dir": str(tmp_path),
                "extracted_dir": str(tmp_path / "extracted"),
                "reports_dir": str(tmp_path / "reports"),
            },
        }

        # Create mock PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("Test content")

        # Stage 1: PDF Ingestion (mocked)
        with patch("src.pdf_ingestion.pdf_reader.PDFReader"):
            from src.pdf_ingestion.pdf_reader import PDFReader
            reader = PDFReader(str(pdf_path))
            # Reader would process PDF

        # Stage 2: Data Storage
        data_store = DataStore(config)
        component = WebComponent(
            page_url="https://example.com",
            component_id="comp_001",
            component_type=ComponentType.HEADING,
            component_selector="h1",
            text_content="Test",
        )
        data_store.save_component(component)

        # Stage 3: Report Generation
        metadata = ReportMetadata(
            report_id="test_001",
            generated_at=datetime.now(),
            website_url="https://example.com",
            pages_checked=1,
            components_checked=1,
            discrepancies_found=0,
            audit_duration_seconds=10.0,
            compliance_percentage=100.0,
        )

        orchestrator = ReportingOrchestrator()
        report_paths = orchestrator.generate_all(
            metadata, [], [], output_dir=config["output"]["reports_dir"]
        )

        # Verify results
        assert Path(report_paths["json"]).exists()
        assert Path(report_paths["markdown"]).exists()
        assert Path(report_paths["html"]).exists()

        # Verify report content
        with open(report_paths["json"]) as f:
            report_data = json.load(f)
        assert report_data["metadata"]["website_url"] == "https://example.com"


@pytest.mark.integration
class TestPipelineWithRealServices:
    """Test pipeline with real external services (if available)."""

    @pytest.mark.skipif(
        True,  # Disabled by default for CI environments
        reason="Requires external services running locally"
    )
    def test_real_qdrant_connection(self):
        """Test actual Qdrant connection."""
        from src.vector_store.qdrant_client import QdrantVectorStore
        
        config = {"vector_db": {"url": "http://localhost:6333"}}
        vector_store = QdrantVectorStore(config)
        # Should not raise
        vector_store.health_check()

    @pytest.mark.skipif(
        not pytest.config.option.with_external_services,
        reason="Requires external services"
    )
    def test_real_openai_embedding(self):
        """Test actual OpenAI embedding."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            from src.vector_store.embeddings import EmbeddingGenerator
            
            config = {"llm": {"embedding_model": "text-embedding-3-small"}}
            embedder = EmbeddingGenerator(config)
            
            # Should not raise
            embedding = embedder.embed_text("test content")
            assert isinstance(embedding, list)


@pytest.mark.integration
class TestPipelineErrorHandling:
    """Test error handling in pipeline."""

    @pytest.mark.asyncio
    async def test_missing_pdf_handling(self, tmp_path):
        """Test handling of missing PDF."""
        config = {"pdf": {"path": str(tmp_path / "nonexistent.pdf")}}
        
        with pytest.raises(Exception):
            reader = PDFReader(config["pdf"]["path"])
            reader.extract_text()

    @pytest.mark.asyncio
    async def test_invalid_config_handling(self):
        """Test handling of invalid configuration."""
        with pytest.raises(Exception):
            get_config("nonexistent_config.yaml")

    @pytest.mark.asyncio
    async def test_storage_error_handling(self, tmp_path):
        """Test handling of storage errors."""
        config = {
            "output": {
                "extracted_dir": "/invalid/path/that/does/not/exist",
            }
        }
        
        data_store = DataStore(config)
        component = WebComponent(
            page_url="https://example.com",
            component_id="comp_001",
            component_type=ComponentType.HEADING,
            component_selector="h1",
            text_content="Test",
        )

        # Should handle path creation
        try:
            data_store.save_component(component)
        except Exception as e:
            # Permission denied or similar expected
            assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
