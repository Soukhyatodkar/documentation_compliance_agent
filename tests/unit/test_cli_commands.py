"""
Unit tests for CLI commands.

Tests all CLI command handlers including:
- run: Full pipeline execution
- ingest: PDF ingestion
- extract: Website extraction
- compare: Component comparison
- report: Report generation
- config: Configuration display
- test-connection: Service connectivity
- status: Project status
- validate-config: Configuration validation
- health-check: System health check
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from typer.testing import CliRunner
from src.cli.commands import app
from src.core.config import Config
from src.data.models import Discrepancy, ComparisonResult, SeverityLevel, ComponentType


runner = CliRunner()


class TestRunCommand:
    """Test the main run command."""

    @patch("src.cli.commands.get_config")
    @patch("src.cli.commands.setup_logging")
    @patch("src.cli.commands._ingest_stage")
    @patch("src.cli.commands._extract_stage")
    @patch("src.cli.commands._compare_stage")
    @patch("src.cli.commands._report_stage")
    def test_run_full_pipeline(self, mock_report, mock_compare, mock_extract, mock_ingest, mock_logging, mock_config):
        """Test full pipeline execution."""
        mock_config_obj = Mock()
        mock_config_obj.app.skip_extraction = False
        mock_config.return_value = mock_config_obj

        mock_compare.return_value = ([], [])
        mock_report.return_value = {"json": "report.json", "markdown": "report.md", "html": "report.html"}

        result = runner.invoke(app, ["run", "--config", "test_config.yaml"])

        assert result.exit_code == 0
        assert "PIPELINE COMPLETE" in result.stdout
        mock_ingest.assert_called_once()
        mock_compare.assert_called_once()
        mock_report.assert_called_once()

    @patch("src.cli.commands.get_config")
    def test_run_dry_run_mode(self, mock_config):
        """Test dry run mode shows config without executing."""
        mock_config_obj = Mock()
        mock_config_obj.website.url = "https://example.com"
        mock_config_obj.pdf.path = "test.pdf"
        mock_config.return_value = mock_config_obj

        result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.stdout

    @patch("src.cli.commands.get_config")
    def test_run_invalid_config(self, mock_config):
        """Test run command with invalid config."""
        from src.core.exceptions import ConfigurationError
        mock_config.side_effect = ConfigurationError("Invalid config")

        result = runner.invoke(app, ["run"])

        assert result.exit_code == 1
        assert "Configuration Error" in result.stdout


class TestIngestCommand:
    """Test the ingest command."""

    @patch("src.cli.commands.get_config")
    @patch("src.cli.commands.setup_logging")
    @patch("src.cli.commands._ingest_stage")
    def test_ingest_success(self, mock_ingest, mock_logging, mock_config):
        """Test successful PDF ingestion."""
        mock_config_obj = Mock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(app, ["ingest", "--config", "test_config.yaml"])

        assert result.exit_code == 0
        assert "PDF ingestion complete" in result.stdout
        mock_ingest.assert_called_once()

    @patch("src.cli.commands.get_config")
    def test_ingest_verbose_logging(self, mock_config):
        """Test ingest with verbose logging."""
        mock_config_obj = Mock()
        mock_config.return_value = mock_config_obj

        with patch("src.cli.commands.setup_logging") as mock_logging:
            result = runner.invoke(app, ["ingest", "--verbose"])
            
            # Verify setup_logging was called with verbose=True
            call_args = mock_logging.call_args
            assert call_args[1].get("verbose") == True


class TestExtractCommand:
    """Test the extract command."""

    @patch("src.cli.commands.get_config")
    @patch("src.cli.commands.setup_logging")
    @patch("src.cli.commands._extract_stage")
    def test_extract_success(self, mock_extract, mock_logging, mock_config):
        """Test successful website extraction."""
        mock_config_obj = Mock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(app, ["extract", "--config", "test_config.yaml"])

        assert result.exit_code == 0
        assert "Website extraction complete" in result.stdout
        mock_extract.assert_called_once()


class TestCompareCommand:
    """Test the compare command."""

    @patch("src.cli.commands.get_config")
    @patch("src.cli.commands.setup_logging")
    @patch("src.cli.commands._compare_stage")
    def test_compare_success(self, mock_compare, mock_logging, mock_config):
        """Test successful comparison."""
        mock_config_obj = Mock()
        mock_config.return_value = mock_config_obj
        mock_compare.return_value = ([], [])

        result = runner.invoke(app, ["compare", "--config", "test_config.yaml"])

        assert result.exit_code == 0
        assert "Comparison complete" in result.stdout
        mock_compare.assert_called_once()


class TestReportCommand:
    """Test the report command."""

    @patch("src.cli.commands.get_config")
    @patch("src.cli.commands.setup_logging")
    @patch("src.cli.commands.DataStore")
    @patch("src.cli.commands._report_stage")
    def test_report_success(self, mock_report, mock_store, mock_logging, mock_config):
        """Test successful report generation."""
        mock_config_obj = Mock()
        mock_config.return_value = mock_config_obj
        
        mock_store_obj = Mock()
        mock_store_obj.get_discrepancies.return_value = []
        mock_store_obj.get_comparison_results.return_value = []
        mock_store.return_value = mock_store_obj

        mock_report.return_value = {"json": "report.json"}

        result = runner.invoke(app, ["report", "--config", "test_config.yaml"])

        assert result.exit_code == 0
        assert "Reports generated" in result.stdout


class TestConfigCommand:
    """Test the config command."""

    @patch("src.cli.commands.get_config")
    def test_config_display(self, mock_config):
        """Test config display."""
        mock_config_obj = Mock()
        mock_config_obj.website.model_dump.return_value = {"url": "https://example.com"}
        mock_config_obj.pdf.model_dump.return_value = {"path": "test.pdf"}
        mock_config_obj.llm.model_dump.return_value = {"model": "gpt-4"}
        mock_config_obj.vector_db.model_dump.return_value = {"url": "http://localhost:6333"}
        mock_config.return_value = mock_config_obj

        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "WEBSITE:" in result.stdout

    @patch("src.cli.commands.get_config")
    def test_config_section_filter(self, mock_config):
        """Test config with section filter."""
        mock_config_obj = Mock()
        mock_config_obj.website.model_dump.return_value = {"url": "https://example.com"}
        mock_config.return_value = mock_config_obj

        result = runner.invoke(app, ["config", "--section", "website"])

        assert result.exit_code == 0


class TestTestConnectionCommand:
    """Test the test-connection command."""

    @patch("src.cli.commands.get_config")
    @patch("src.cli.commands.setup_logging")
    @patch("src.cli.commands.QdrantVectorStore")
    @patch("src.cli.commands.EmbeddingGenerator")
    def test_test_connection_success(self, mock_embedder, mock_vector_store, mock_logging, mock_config):
        """Test successful connection test."""
        mock_config_obj = Mock()
        mock_config_obj.website.url = "https://example.com"
        mock_config_obj.pdf.path = "test.pdf"
        mock_config.return_value = mock_config_obj

        mock_vector_store_obj = Mock()
        mock_vector_store_obj.health_check.return_value = None
        mock_vector_store.return_value = mock_vector_store_obj

        mock_embedder_obj = Mock()
        mock_embedder_obj.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_embedder.return_value = mock_embedder_obj

        # Mock Path.exists
        with patch("pathlib.Path.exists", return_value=True):
            result = runner.invoke(app, ["test-connection"])

            assert result.exit_code == 0
            assert "Qdrant" in result.stdout


class TestStatusCommand:
    """Test the status command."""

    @patch("src.cli.commands.get_config")
    @patch("src.cli.commands.setup_logging")
    @patch("src.cli.commands.DataStore")
    def test_status_display(self, mock_store, mock_logging, mock_config):
        """Test status display."""
        mock_config_obj = Mock()
        mock_config_obj.output.reports_dir = "data/reports"
        mock_config.return_value = mock_config_obj

        mock_store_obj = Mock()
        mock_store_obj.count_components.return_value = 10
        mock_store_obj.count_comparison_results.return_value = 5
        mock_store_obj.count_discrepancies.return_value = 2
        mock_store.return_value = mock_store_obj

        with patch("pathlib.Path.exists", return_value=False):
            result = runner.invoke(app, ["status"])

            assert result.exit_code == 0
            assert "Components" in result.stdout


class TestValidateConfigCommand:
    """Test the validate-config command."""

    @patch("src.cli.commands.get_config")
    def test_validate_config_success(self, mock_config):
        """Test successful config validation."""
        mock_config_obj = Mock()
        mock_config_obj.website.url = "https://example.com"
        mock_config_obj.pdf.path = "test.pdf"
        mock_config_obj.llm.model = "gpt-4"
        mock_config_obj.vector_db.url = "http://localhost:6333"
        mock_config.return_value = mock_config_obj

        result = runner.invoke(app, ["validate-config"])

        assert result.exit_code == 0
        assert "Configuration is valid" in result.stdout

    @patch("src.cli.commands.get_config")
    def test_validate_config_failure(self, mock_config):
        """Test config validation failure."""
        from src.core.exceptions import ConfigurationError
        mock_config.side_effect = ConfigurationError("Invalid config")

        result = runner.invoke(app, ["validate-config"])

        assert result.exit_code == 1
        assert "Configuration Error" in result.stdout


class TestHealthCheckCommand:
    """Test the health-check command."""

    @patch("src.cli.commands.get_config")
    @patch("src.cli.commands.setup_logging")
    @patch("src.cli.commands.QdrantVectorStore")
    @patch("src.cli.commands.EmbeddingGenerator")
    def test_health_check_success(self, mock_embedder, mock_vector_store, mock_logging, mock_config):
        """Test successful health check."""
        mock_config_obj = Mock()
        mock_config_obj.output.pdfs_dir = "data/pdfs"
        mock_config_obj.output.extracted_dir = "data/extracted"
        mock_config_obj.output.screenshots_dir = "data/screenshots"
        mock_config_obj.output.reports_dir = "data/reports"
        mock_config_obj.output.logs_dir = "logs"
        mock_config_obj.pdf.path = "test.pdf"
        mock_config.return_value = mock_config_obj

        mock_vector_store_obj = Mock()
        mock_vector_store_obj.health_check.return_value = None
        mock_vector_store.return_value = mock_vector_store_obj

        mock_embedder_obj = Mock()
        mock_embedder_obj.embed_text.return_value = [0.1, 0.2]
        mock_embedder.return_value = mock_embedder_obj

        with patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.exists", return_value=True):
            result = runner.invoke(app, ["health-check"])

            assert result.exit_code == 0
            assert "System health" in result.stdout


class TestVersionCommand:
    """Test the version command."""

    def test_version_display(self):
        """Test version display."""
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "Documentation Compliance Agent" in result.stdout
        assert "1.0.0" in result.stdout


class TestCliHelp:
    """Test CLI help functionality."""

    def test_main_help(self):
        """Test main help output."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "run" in result.stdout
        assert "ingest" in result.stdout
        assert "extract" in result.stdout

    def test_command_help(self):
        """Test individual command help."""
        result = runner.invoke(app, ["run", "--help"])

        assert result.exit_code == 0
        assert "Full pipeline" in result.stdout or "pipeline" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
