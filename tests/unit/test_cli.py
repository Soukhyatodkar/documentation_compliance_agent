"""
Unit tests for CLI module.

This module tests all CLI commands including:
- Pipeline commands (run, ingest, extract, compare, report)
- Utility commands (config, test-connection, status, version)
- Error handling and edge cases
- Output formatting and help text
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from src.cli.commands import (
    app,
    _calculate_compliance_score,
    _ingest_stage,
    _compare_stage,
    _report_stage,
    _show_config_summary,
)
from src.core.exceptions import (
    ConfigurationError,
    ProcessingError,
)
from src.data.models import ComparisonResult, Discrepancy, WebComponent, ComplianceStatus

runner = CliRunner()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = MagicMock()
    config.app.skip_extraction = False
    config.website.url = "https://example.com"
    config.pdf.path = "data/pdfs/test.pdf"
    config.output.reports_dir = "data/reports"
    config.llm.model = "gpt-4"
    config.vector_db.url = "http://localhost:6333"
    return config


@pytest.fixture
def sample_component():
    """Create a sample component for testing."""
    return WebComponent(
        id="comp_001",
        page_url="https://example.com/page1",
        component_type="button",
        component_selector="#submit-btn",
        content="Submit",
        element_html="<button id='submit-btn'>Submit</button>",
        screenshot_path="data/screenshots/btn_001.png",
        extracted_at=datetime.now(),
        metadata={"role": "submit"},
    )


@pytest.fixture
def sample_comparison_result(sample_component):
    """Create a sample comparison result."""
    return ComparisonResult(
        id="result_001",
        component_id=sample_component.id,
        page_url=sample_component.page_url,
        component_type=sample_component.component_type,
        status=ComparisonStatus.COMPLIANT,
        assessment_summary="Component complies with guidelines",
        reasoning="Button text is clear and descriptive",
        confidence_score=0.95,
        retrieved_guidelines=["Use clear button labels", "Ensure accessibility"],
        comparison_timestamp=datetime.now(),
        llm_model="gpt-4",
        processing_time_seconds=2.5,
    )


@pytest.fixture
def sample_discrepancy(sample_component):
    """Create a sample discrepancy."""
    return Discrepancy(
        id="disc_001",
        component_id=sample_component.id,
        page_url=sample_component.page_url,
        component_type=sample_component.component_type,
        component_selector=sample_component.component_selector,
        actual_content=sample_component.content,
        expected_content="Submit Form",
        discrepancy_type="CONTENT_MISMATCH",
        severity="HIGH",
        description="Button label does not match guideline",
        guideline_chunk_id="chunk_123",
        guideline_section="Button Labels",
        confidence_score=0.85,
        remediation_suggestion="Change button text to 'Submit Form'",
        detected_at=datetime.now().isoformat(),
        metadata={"impact": "high", "effort": "low"},
    )


# ============================================================================
# Main Pipeline Command Tests
# ============================================================================


class TestRunCommand:
    """Tests for the 'run' command."""

    def test_run_success(self, mock_config):
        """Test successful pipeline execution."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands._ingest_stage"), patch(
            "src.cli.commands._extract_stage"
        ), patch(
            "src.cli.commands._compare_stage", return_value=([], [])
        ), patch(
            "src.cli.commands._report_stage", return_value={"json": "report.json"}
        ):
            result = runner.invoke(app, ["run", "--config", "config/test.yaml"])
            assert result.exit_code == 0
            assert "PIPELINE COMPLETE" in result.stdout

    def test_run_with_verbose(self, mock_config):
        """Test run command with verbose logging."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands._ingest_stage"), patch(
            "src.cli.commands._extract_stage"
        ), patch(
            "src.cli.commands._compare_stage", return_value=([], [])
        ), patch(
            "src.cli.commands._report_stage", return_value={"json": "report.json"}
        ):
            result = runner.invoke(app, ["run", "--verbose"])
            assert result.exit_code == 0

    def test_run_dry_run(self, mock_config):
        """Test run command in dry-run mode."""
        with patch(
            "src.cli.commands.get_config", return_value=mock_config
        ), patch("src.cli.commands._show_config_summary"):
            result = runner.invoke(app, ["run", "--dry-run"])
            assert result.exit_code == 0
            assert "DRY RUN" in result.stdout

    def test_run_config_error(self):
        """Test run command with invalid config."""
        with patch(
            "src.cli.commands.get_config", side_effect=ConfigurationError("Invalid config")
        ):
            result = runner.invoke(app, ["run", "--config", "invalid.yaml"])
            assert result.exit_code == 1
            assert "Configuration Error" in result.stdout

    def test_run_unexpected_error(self, mock_config):
        """Test run command with unexpected error."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands._ingest_stage", side_effect=RuntimeError("Unknown error")):
            result = runner.invoke(app, ["run"])
            assert result.exit_code == 1
            assert "Pipeline Error" in result.stdout


# ============================================================================
# Individual Stage Command Tests
# ============================================================================


class TestIngestCommand:
    """Tests for the 'ingest' command."""

    def test_ingest_success(self, mock_config):
        """Test successful PDF ingestion."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands._ingest_stage"):
            result = runner.invoke(app, ["ingest"])
            assert result.exit_code == 0
            assert "PDF ingestion complete" in result.stdout

    def test_ingest_error(self, mock_config):
        """Test ingest command with error."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands._ingest_stage", side_effect=ProcessingError("PDF error")):
            result = runner.invoke(app, ["ingest"])
            assert result.exit_code == 1
            assert "Ingestion Error" in result.stdout


class TestExtractCommand:
    """Tests for the 'extract' command."""

    def test_extract_success(self, mock_config):
        """Test successful website extraction."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands._extract_stage"):
            result = runner.invoke(app, ["extract"])
            assert result.exit_code == 0
            assert "Website extraction complete" in result.stdout

    def test_extract_error(self, mock_config):
        """Test extract command with error."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands._extract_stage", side_effect=Exception("Extract failed")):
            result = runner.invoke(app, ["extract"])
            assert result.exit_code == 1
            assert "Extraction Error" in result.stdout


class TestCompareCommand:
    """Tests for the 'compare' command."""

    @pytest.mark.asyncio
    async def test_compare_success(self, mock_config):
        """Test successful component comparison."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch(
            "src.cli.commands._compare_stage", return_value=([], [])
        ) as mock_compare:
            result = runner.invoke(app, ["compare"])
            assert result.exit_code == 0
            assert "Comparison complete" in result.stdout

    def test_compare_error(self, mock_config):
        """Test compare command with error."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch(
            "src.cli.commands._compare_stage", side_effect=Exception("Compare failed")
        ):
            result = runner.invoke(app, ["compare"])
            assert result.exit_code == 1
            assert "Comparison Error" in result.stdout


class TestReportCommand:
    """Tests for the 'report' command."""

    def test_report_success(self, mock_config):
        """Test successful report generation."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands.DataStore"), patch(
            "src.cli.commands._report_stage",
            return_value={"json": "report.json", "markdown": "report.md", "html": "report.html"},
        ):
            result = runner.invoke(app, ["report"])
            assert result.exit_code == 0
            assert "Reports generated" in result.stdout

    def test_report_error(self, mock_config):
        """Test report command with error."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands.DataStore", side_effect=Exception("Storage error")):
            result = runner.invoke(app, ["report"])
            assert result.exit_code == 1
            assert "Report Generation Error" in result.stdout


# ============================================================================
# Utility Command Tests
# ============================================================================


class TestConfigCommand:
    """Tests for the 'config' command."""

    def test_config_show_all(self, mock_config):
        """Test showing all configuration."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands._show_config_summary"
        ):
            result = runner.invoke(app, ["config"])
            assert result.exit_code == 0
            assert "Configuration" in result.stdout

    def test_config_show_section(self, mock_config):
        """Test showing specific configuration section."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands._show_config_summary"
        ):
            result = runner.invoke(app, ["config", "--section", "website"])
            assert result.exit_code == 0


class TestTestConnectionCommand:
    """Tests for the 'test-connection' command."""

    def test_test_connection_success(self, mock_config):
        """Test successful connection testing."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands.QdrantVectorStore") as mock_qdrant, patch(
            "src.cli.commands.EmbeddingGenerator"
        ) as mock_embedder, patch(
            "src.cli.commands.asyncio.run"
        ):
            mock_qdrant_instance = MagicMock()
            mock_qdrant_instance.health_check.return_value = None
            mock_qdrant.return_value = mock_qdrant_instance

            mock_embedder_instance = MagicMock()
            mock_embedder_instance.embed_text.return_value = [0.1, 0.2]
            mock_embedder.return_value = mock_embedder_instance

            result = runner.invoke(app, ["test-connection"])
            assert result.exit_code == 0
            assert "Connection test complete" in result.stdout


class TestStatusCommand:
    """Tests for the 'status' command."""

    def test_status_success(self, mock_config):
        """Test status command."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands.DataStore") as mock_store, patch(
            "src.cli.commands.Path"
        ):
            mock_store_instance = MagicMock()
            mock_store_instance.count_components.return_value = 10
            mock_store_instance.count_comparison_results.return_value = 8
            mock_store_instance.count_discrepancies.return_value = 2
            mock_store.return_value = mock_store_instance

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "Project Status" in result.stdout


class TestVersionCommand:
    """Tests for the 'version' command."""

    def test_version_display(self):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Version" in result.stdout


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestCalculateComplianceScore:
    """Tests for _calculate_compliance_score function."""

    def test_empty_results(self):
        """Test with empty results."""
        score = _calculate_compliance_score([])
        assert score == 100.0

    def test_all_compliant(self, sample_comparison_result):
        """Test with all compliant components."""
        results = [sample_comparison_result] * 5
        score = _calculate_compliance_score(results)
        assert score == 100.0

    def test_partial_compliance(self, sample_comparison_result):
        """Test with partial compliance."""
        compliant_result = sample_comparison_result
        non_compliant = MagicMock()
        non_compliant.status.value = "non_compliant"

        results = [compliant_result] * 3 + [non_compliant] * 2
        score = _calculate_compliance_score(results)
        assert score == 60.0


class TestShowConfigSummary:
    """Tests for _show_config_summary function."""

    def test_show_all_config(self, mock_config):
        """Test showing all configuration."""
        with patch("typer.echo"):
            # Should not raise an exception
            _show_config_summary(mock_config)

    def test_show_specific_section(self, mock_config):
        """Test showing specific section."""
        with patch("typer.echo"):
            _show_config_summary(mock_config, section="website")

    def test_show_invalid_section(self, mock_config):
        """Test showing invalid section."""
        with patch("typer.echo"):
            _show_config_summary(mock_config, section="invalid_section")


# ============================================================================
# Integration Tests
# ============================================================================


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def test_help_text(self):
        """Test help text is available."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Documentation Compliance Agent" in result.stdout

    def test_command_help(self):
        """Test individual command help."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "complete compliance checking pipeline" in result.stdout.lower()

    def test_invalid_command(self):
        """Test invalid command."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

    def test_command_with_short_options(self, mock_config):
        """Test commands with short option flags."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands._ingest_stage"):
            result = runner.invoke(app, ["ingest", "-c", "config/test.yaml", "-v"])
            assert result.exit_code == 0


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_cli_with_missing_config_file(self):
        """Test CLI with missing config file."""
        with patch(
            "src.cli.commands.get_config", side_effect=FileNotFoundError("Config not found")
        ):
            result = runner.invoke(app, ["run", "--config", "nonexistent.yaml"])
            assert result.exit_code == 1

    def test_cli_handles_unicode_output(self, mock_config):
        """Test CLI handles unicode in output."""
        with patch("src.cli.commands.get_config", return_value=mock_config):
            result = runner.invoke(app, ["version"])
            assert result.exit_code == 0

    def test_cli_timeout_handling(self, mock_config):
        """Test CLI handles timeouts gracefully."""
        with patch("src.cli.commands.get_config", return_value=mock_config), patch(
            "src.cli.commands.setup_logging"
        ), patch("src.cli.commands._ingest_stage", side_effect=TimeoutError("Request timeout")):
            result = runner.invoke(app, ["ingest"])
            assert result.exit_code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
