"""
Unit tests for report generation.

Tests all report generation functionality including:
- JSON report generation
- Markdown report generation
- HTML report generation
- Report aggregation
- Statistics calculation
- Recommendations generation
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.reporting.report_generator import (
    ReportMetadata,
    JSONReportGenerator,
    MarkdownReportGenerator,
    HTMLReportGenerator,
    ReportingOrchestrator,
)
from src.data.models import (
    Discrepancy,
    ComparisonResult,
    SeverityLevel,
    ComponentType,
    DiscrepancyType,
    ComplianceStatus,
)
from src.core.exceptions import ReportGenerationError


class TestReportMetadata:
    """Test ReportMetadata model."""

    def test_metadata_creation(self):
        """Test creating valid metadata."""
        metadata = ReportMetadata(
            report_id="test_report_001",
            generated_at=datetime.now(),
            website_url="https://example.com",
            pages_checked=10,
            components_checked=50,
            discrepancies_found=5,
            audit_duration_seconds=120.5,
            compliance_percentage=90.0,
        )

        assert metadata.report_id == "test_report_001"
        assert metadata.website_url == "https://example.com"
        assert metadata.pages_checked == 10
        assert metadata.compliance_percentage == 90.0

    def test_metadata_validation(self):
        """Test metadata validation."""
        with pytest.raises(Exception):
            # Compliance percentage out of range
            ReportMetadata(
                report_id="test",
                generated_at=datetime.now(),
                website_url="https://example.com",
                pages_checked=10,
                components_checked=50,
                discrepancies_found=5,
                audit_duration_seconds=120.5,
                compliance_percentage=150.0,  # Invalid
            )


class TestJSONReportGenerator:
    """Test JSON report generation."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return JSONReportGenerator()

    @pytest.fixture
    def metadata(self):
        """Create test metadata."""
        return ReportMetadata(
            report_id="test_report",
            generated_at=datetime(2024, 1, 1, 12, 0, 0),
            website_url="https://example.com",
            pages_checked=5,
            components_checked=20,
            discrepancies_found=2,
            audit_duration_seconds=300.0,
            compliance_percentage=90.0,
        )

    @pytest.fixture
    def sample_discrepancies(self):
        """Create sample discrepancies."""
        return [
            Discrepancy(
                discrepancy_id="disc_001",
                page_url="https://example.com/page1",
                component_id="comp_001",
                component_type=ComponentType.HEADING,
                component_selector="h1.title",
                actual_content="Welcome to Our Site",
                expected_content="Welcome to Example.com",
                guideline_chunk_id="chunk_001",
                guideline_section="Section 2.1",
                discrepancy_type=DiscrepancyType.TEXT_MISMATCH,
                severity=SeverityLevel.WARNING,
                confidence_score=0.95,
                reason="Header text differs from guideline",
                remediation_suggestion="Update header text to match guideline",
                detected_at=datetime.now(),
            ),
            Discrepancy(
                discrepancy_id="disc_002",
                page_url="https://example.com/page2",
                component_id="comp_002",
                component_type=ComponentType.BUTTON,
                component_selector="button.submit",
                actual_content="",
                expected_content="Submit Form",
                guideline_chunk_id="chunk_002",
                guideline_section="Section 3.2",
                discrepancy_type=DiscrepancyType.MISSING_COMPONENT,
                severity=SeverityLevel.CRITICAL,
                confidence_score=0.99,
                reason="Button label is missing",
                remediation_suggestion="Add button label",
                detected_at=datetime.now(),
            ),
        ]

    def test_json_report_generation(self, generator, metadata, sample_discrepancies):
        """Test JSON report generation."""
        results = []
        report = generator.generate(metadata, results, sample_discrepancies)

        assert "metadata" in report
        assert "summary" in report
        assert "discrepancies" in report
        assert "statistics" in report
        assert "recommendations" in report

        assert report["metadata"]["website_url"] == "https://example.com"
        assert len(report["discrepancies"]) == 2

    def test_json_report_statistics(self, generator, metadata, sample_discrepancies):
        """Test statistics aggregation."""
        results = []
        report = generator.generate(metadata, results, sample_discrepancies)

        stats = report["statistics"]
        assert stats["critical_count"] == 1
        assert stats["warning_count"] == 1
        assert stats["by_severity"]["critical"] == 1
        assert stats["by_severity"]["warning"] == 1

    def test_json_report_recommendations(self, generator, metadata, sample_discrepancies):
        """Test recommendations generation."""
        results = []
        report = generator.generate(metadata, results, sample_discrepancies)

        recommendations = report["recommendations"]
        assert len(recommendations) > 0
        assert any("critical" in r.lower() for r in recommendations)

    def test_json_report_save(self, generator, metadata, sample_discrepancies, tmp_path):
        """Test saving JSON report to file."""
        output_path = tmp_path / "report.json"
        results = []
        
        report = generator.generate(
            metadata, results, sample_discrepancies, output_path=str(output_path)
        )

        assert output_path.exists()
        with open(output_path) as f:
            saved_report = json.load(f)
        assert saved_report["metadata"]["report_id"] == "test_report"

    def test_discrepancy_formatting(self, generator, sample_discrepancies):
        """Test discrepancy formatting for JSON."""
        formatted = generator._format_discrepancy(sample_discrepancies[0])

        assert formatted["page_url"] == "https://example.com/page1"
        assert formatted["component_type"] == ComponentType.HEADING.value
        assert formatted["severity"] == SeverityLevel.WARNING.value
        assert formatted["confidence"] == 0.95


class TestMarkdownReportGenerator:
    """Test Markdown report generation."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return MarkdownReportGenerator()

    @pytest.fixture
    def metadata(self):
        """Create test metadata."""
        return ReportMetadata(
            report_id="test_report",
            generated_at=datetime(2024, 1, 1, 12, 0, 0),
            website_url="https://example.com",
            pages_checked=5,
            components_checked=20,
            discrepancies_found=2,
            audit_duration_seconds=300.0,
            compliance_percentage=90.0,
        )

    @pytest.fixture
    def sample_discrepancies(self):
        """Create sample discrepancies."""
        return [
            Discrepancy(
                discrepancy_id="disc_001",
                page_url="https://example.com/page1",
                component_id="comp_001",
                component_type=ComponentType.HEADING,
                component_selector="h1.title",
                actual_content="Welcome to Our Site",
                expected_content="Welcome to Example.com",
                guideline_chunk_id="chunk_001",
                guideline_section="Section 2.1",
                discrepancy_type=DiscrepancyType.TEXT_MISMATCH,
                severity=SeverityLevel.WARNING,
                confidence_score=0.95,
                reason="Header text differs from guideline",
                remediation_suggestion="Update header text to match guideline",
                detected_at=datetime.now(),
            ),
        ]

    def test_markdown_report_generation(self, generator, metadata, sample_discrepancies):
        """Test Markdown report generation."""
        results = []
        report = generator.generate(metadata, results, sample_discrepancies)

        assert isinstance(report, str)
        assert "Compliance Audit Report" in report
        assert "Executive Summary" in report
        assert "Detailed Findings" in report

    def test_markdown_report_structure(self, generator, metadata, sample_discrepancies):
        """Test Markdown report structure."""
        results = []
        report = generator.generate(metadata, results, sample_discrepancies)

        assert "Overall Compliance:" in report
        assert "Pages Audited:" in report
        assert "Components Checked:" in report
        assert "Issues Found:" in report

    def test_markdown_report_severity_icons(self, generator, metadata, sample_discrepancies):
        """Test severity icons in Markdown."""
        results = []
        report = generator.generate(metadata, results, sample_discrepancies)

        # Check for emoji icons
        assert "🟡" in report or "WARNING" in report

    def test_markdown_report_save(self, generator, metadata, sample_discrepancies, tmp_path):
        """Test saving Markdown report."""
        output_path = tmp_path / "report.md"
        results = []
        
        report = generator.generate(
            metadata, results, sample_discrepancies, output_path=str(output_path)
        )

        assert output_path.exists()
        with open(output_path) as f:
            content = f.read()
        assert "Compliance Audit Report" in content

    def test_markdown_empty_findings(self, generator, metadata):
        """Test Markdown with no discrepancies."""
        results = []
        report = generator.generate(metadata, results, [])

        assert "No compliance issues found" in report


class TestHTMLReportGenerator:
    """Test HTML report generation."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return HTMLReportGenerator()

    @pytest.fixture
    def metadata(self):
        """Create test metadata."""
        return ReportMetadata(
            report_id="test_report",
            generated_at=datetime(2024, 1, 1, 12, 0, 0),
            website_url="https://example.com",
            pages_checked=5,
            components_checked=20,
            discrepancies_found=2,
            audit_duration_seconds=300.0,
            compliance_percentage=90.0,
        )

    @pytest.fixture
    def sample_discrepancies(self):
        """Create sample discrepancies."""
        return [
            Discrepancy(
                discrepancy_id="disc_001",
                page_url="https://example.com/page1",
                component_id="comp_001",
                component_type=ComponentType.HEADING,
                component_selector="h1.title",
                actual_content="Welcome to Our Site",
                expected_content="Welcome to Example.com",
                guideline_chunk_id="chunk_001",
                guideline_section="Section 2.1",
                discrepancy_type=DiscrepancyType.TEXT_MISMATCH,
                severity=SeverityLevel.WARNING,
                confidence_score=0.95,
                reason="Header text differs from guideline",
                remediation_suggestion="Update header text to match guideline",
                detected_at=datetime.now(),
            ),
        ]

    def test_html_report_generation(self, generator, metadata, sample_discrepancies):
        """Test HTML report generation."""
        results = []
        report = generator.generate(metadata, results, sample_discrepancies)

        assert isinstance(report, str)
        assert "<!DOCTYPE html>" in report
        assert "Compliance Audit Report" in report

    def test_html_report_structure(self, generator, metadata, sample_discrepancies):
        """Test HTML structure."""
        results = []
        report = generator.generate(metadata, results, sample_discrepancies)

        assert "<table>" in report
        assert "<thead>" in report
        assert "<tbody>" in report
        assert "90.0%" in report  # Compliance percentage

    def test_html_report_save(self, generator, metadata, sample_discrepancies, tmp_path):
        """Test saving HTML report."""
        output_path = tmp_path / "report.html"
        results = []
        
        report = generator.generate(
            metadata, results, sample_discrepancies, output_path=str(output_path)
        )

        assert output_path.exists()
        with open(output_path) as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content


class TestReportingOrchestrator:
    """Test reporting orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return ReportingOrchestrator()

    @pytest.fixture
    def metadata(self):
        """Create test metadata."""
        return ReportMetadata(
            report_id="test_report",
            generated_at=datetime(2024, 1, 1, 12, 0, 0),
            website_url="https://example.com",
            pages_checked=5,
            components_checked=20,
            discrepancies_found=0,
            audit_duration_seconds=300.0,
            compliance_percentage=100.0,
        )

    def test_generate_all_formats(self, orchestrator, metadata, tmp_path):
        """Test generating all report formats."""
        results = []
        discrepancies = []
        
        report_paths = orchestrator.generate_all(
            metadata, results, discrepancies, output_dir=str(tmp_path)
        )

        assert "json" in report_paths
        assert "markdown" in report_paths
        assert "html" in report_paths

        assert Path(report_paths["json"]).exists()
        assert Path(report_paths["markdown"]).exists()
        assert Path(report_paths["html"]).exists()

    def test_generate_all_creates_directory(self, orchestrator, metadata, tmp_path):
        """Test that generate_all creates output directory."""
        output_dir = tmp_path / "reports"
        results = []
        discrepancies = []

        report_paths = orchestrator.generate_all(
            metadata, results, discrepancies, output_dir=str(output_dir)
        )

        assert output_dir.exists()
        assert len(report_paths) == 3


class TestReportGenerationErrors:
    """Test error handling in report generation."""

    def test_json_generation_error(self):
        """Test JSON generation error handling."""
        generator = JSONReportGenerator()
        
        with pytest.raises(ReportGenerationError):
            # Pass invalid data that will cause serialization error
            generator.generate(None, None, None)

    def test_markdown_generation_error(self):
        """Test Markdown generation error handling."""
        generator = MarkdownReportGenerator()
        
        with pytest.raises(ReportGenerationError):
            # Pass None metadata that will cause attribute error
            generator.generate(None, None, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
