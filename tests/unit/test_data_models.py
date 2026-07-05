"""
Unit tests for canonical data models.

Tests all data models defined in src/data/models.py including:
- Enums (ComponentType, SeverityLevel, ComplianceStatus)
- Web extraction models
- Guideline models
- Discrepancy models
- Comparison models
- Statistics models
"""

import pytest
from datetime import datetime
from src.data.models import (
    # Enums
    ComponentType,
    SeverityLevel,
    ComplianceStatus,
    # Web models
    WebComponent,
    WebPage,
    WebsiteExtraction,
    # Guideline models
    GuidelineChunk,
    # Discrepancy models
    Discrepancy,
    DiscrepancyReport,
    # Comparison models
    ComparisonContext,
    ComparisonResult,
    # Stats models
    PageStats,
    ComponentStats,
    ComplianceStats,
)


class TestEnums:
    """Test enum definitions."""

    def test_component_type_enum_values(self):
        """Test ComponentType enum has correct values."""
        assert ComponentType.TEXT.value == "text"
        assert ComponentType.HEADING.value == "heading"
        assert ComponentType.BUTTON.value == "button"
        assert ComponentType.LINK.value == "link"
        assert ComponentType.FORM.value == "form"
        assert ComponentType.INPUT.value == "input"
        assert ComponentType.IMAGE.value == "image"
        assert ComponentType.TABLE.value == "table"
        assert ComponentType.DROPDOWN.value == "dropdown"
        assert ComponentType.MODAL.value == "modal"
        assert ComponentType.ALERT.value == "alert"
        assert ComponentType.NAVIGATION.value == "navigation"
        assert ComponentType.CARD.value == "card"
        assert ComponentType.ICON.value == "icon"
        assert ComponentType.OTHER.value == "other"

    def test_severity_level_enum_values(self):
        """Test SeverityLevel enum has correct values."""
        assert SeverityLevel.CRITICAL.value == "critical"
        assert SeverityLevel.WARNING.value == "warning"
        assert SeverityLevel.INFO.value == "info"
        assert SeverityLevel.NOTE.value == "note"

    def test_compliance_status_enum_values(self):
        """Test ComplianceStatus enum has correct values."""
        assert ComplianceStatus.COMPLIANT.value == "compliant"
        assert ComplianceStatus.NON_COMPLIANT.value == "non_compliant"
        assert ComplianceStatus.PARTIAL.value == "partial"
        assert ComplianceStatus.UNKNOWN.value == "unknown"


class TestWebComponent:
    """Test WebComponent model."""

    def test_web_component_minimal(self):
        """Test creating WebComponent with minimal fields."""
        component = WebComponent(
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            selector="button.primary",
            actual_text="Click here",
        )
        assert component.component_id == "comp_1"
        assert component.component_type == ComponentType.BUTTON
        assert component.selector == "button.primary"
        assert component.actual_text == "Click here"
        assert component.actual_html is None
        assert component.attributes == {}
        assert component.position == {}
        assert component.screenshot_path is None

    def test_web_component_full(self):
        """Test creating WebComponent with all fields."""
        component = WebComponent(
            component_id="comp_1",
            component_type=ComponentType.FORM,
            selector="form#login",
            actual_text="Login Form",
            actual_html="<form id='login'>...</form>",
            attributes={"id": "login", "method": "POST"},
            position={"x": 100, "y": 200, "width": 300, "height": 150},
            screenshot_path="/data/screenshots/comp_1.png",
        )
        assert component.component_id == "comp_1"
        assert component.component_type == ComponentType.FORM
        assert component.attributes == {"id": "login", "method": "POST"}
        assert component.position["x"] == 100
        assert component.screenshot_path == "/data/screenshots/comp_1.png"

    def test_web_component_serialization(self):
        """Test WebComponent JSON serialization."""
        component = WebComponent(
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            selector="button.primary",
            actual_text="Click",
        )
        data = component.dict()
        assert data["component_type"] == "button"
        assert isinstance(data, dict)
        assert data["component_id"] == "comp_1"


class TestWebPage:
    """Test WebPage model."""

    def test_web_page_minimal(self):
        """Test creating WebPage with minimal fields."""
        page = WebPage(
            page_id="page_1",
            url="https://example.com",
            title="Example Page",
            page_text="Some text content",
        )
        assert page.page_id == "page_1"
        assert page.url == "https://example.com"
        assert page.title == "Example Page"
        assert page.page_text == "Some text content"
        assert page.description is None
        assert page.components == []
        assert page.screenshot_path is None
        assert page.extraction_duration_seconds == 0.0

    def test_web_page_with_components(self):
        """Test WebPage with components."""
        component = WebComponent(
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            selector="button",
            actual_text="Click",
        )
        page = WebPage(
            page_id="page_1",
            url="https://example.com",
            title="Example",
            page_text="Text",
            components=[component],
            extraction_duration_seconds=2.5,
        )
        assert len(page.components) == 1
        assert page.components[0].component_id == "comp_1"
        assert page.extraction_duration_seconds == 2.5

    def test_web_page_timestamp_auto_generated(self):
        """Test WebPage has auto-generated timestamp."""
        page = WebPage(
            page_id="page_1",
            url="https://example.com",
            title="Example",
            page_text="Text",
        )
        assert page.extracted_at is not None
        # Should be ISO format
        datetime.fromisoformat(page.extracted_at)

    def test_web_page_serialization(self):
        """Test WebPage JSON serialization."""
        page = WebPage(
            page_id="page_1",
            url="https://example.com",
            title="Example",
            page_text="Text",
        )
        data = page.dict()
        assert isinstance(data["extracted_at"], str)
        assert data["page_id"] == "page_1"


class TestWebsiteExtraction:
    """Test WebsiteExtraction model."""

    def test_website_extraction_minimal(self):
        """Test creating WebsiteExtraction with minimal fields."""
        extraction = WebsiteExtraction(
            extraction_id="ext_1",
            website_url="https://example.com",
            total_pages_extracted=5,
            total_pages_attempted=5,
        )
        assert extraction.extraction_id == "ext_1"
        assert extraction.website_url == "https://example.com"
        assert extraction.total_pages_extracted == 5
        assert extraction.total_pages_attempted == 5
        assert extraction.pages == []
        assert extraction.extraction_errors == []

    def test_website_extraction_with_pages(self):
        """Test WebsiteExtraction with pages."""
        page = WebPage(
            page_id="page_1",
            url="https://example.com",
            title="Example",
            page_text="Text",
        )
        extraction = WebsiteExtraction(
            extraction_id="ext_1",
            website_url="https://example.com",
            pages=[page],
            total_pages_extracted=1,
            total_pages_attempted=1,
        )
        assert len(extraction.pages) == 1
        assert extraction.pages[0].page_id == "page_1"

    def test_website_extraction_with_errors(self):
        """Test WebsiteExtraction with extraction errors."""
        extraction = WebsiteExtraction(
            extraction_id="ext_1",
            website_url="https://example.com",
            total_pages_extracted=4,
            total_pages_attempted=5,
            extraction_errors=["Failed to extract page /about"],
        )
        assert len(extraction.extraction_errors) == 1
        assert extraction.total_pages_attempted == 5

    def test_website_extraction_timestamps(self):
        """Test WebsiteExtraction has timestamps."""
        extraction = WebsiteExtraction(
            extraction_id="ext_1",
            website_url="https://example.com",
            total_pages_extracted=0,
            total_pages_attempted=0,
        )
        assert extraction.started_at is not None
        assert extraction.completed_at is None
        # Can set completed_at
        extraction.completed_at = datetime.now().isoformat()
        assert extraction.completed_at is not None


class TestGuidelineChunk:
    """Test GuidelineChunk model."""

    def test_guideline_chunk_minimal(self):
        """Test creating GuidelineChunk with minimal fields."""
        chunk = GuidelineChunk(
            chunk_id="chunk_1",
            text="Guideline text content",
            page_num=1,
            embedding=[0.1, 0.2, 0.3],
        )
        assert chunk.chunk_id == "chunk_1"
        assert chunk.text == "Guideline text content"
        assert chunk.page_num == 1
        assert len(chunk.embedding) == 3
        assert chunk.section is None
        assert chunk.heading is None

    def test_guideline_chunk_full(self):
        """Test creating GuidelineChunk with all fields."""
        embedding = [0.1] * 1536  # Realistic embedding size
        chunk = GuidelineChunk(
            chunk_id="chunk_1",
            text="Guideline text",
            page_num=2,
            section="section_1",
            heading="Authentication Policy",
            embedding=embedding,
        )
        assert chunk.section == "section_1"
        assert chunk.heading == "Authentication Policy"
        assert len(chunk.embedding) == 1536


class TestDiscrepancy:
    """Test Discrepancy model."""

    def test_discrepancy_minimal(self):
        """Test creating Discrepancy with required fields."""
        discrepancy = Discrepancy(
            discrepancy_id="disc_1",
            page_url="https://example.com/login",
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            component_selector="button.submit",
            actual_content="Sign In",
            guideline_chunk_id="chunk_1",
            severity=SeverityLevel.WARNING,
            confidence_score=0.85,
            reason="Button text differs from guideline",
        )
        assert discrepancy.discrepancy_id == "disc_1"
        assert discrepancy.page_url == "https://example.com/login"
        assert discrepancy.actual_content == "Sign In"
        assert discrepancy.severity == SeverityLevel.WARNING
        assert discrepancy.confidence_score == 0.85

    def test_discrepancy_full(self):
        """Test creating Discrepancy with all fields."""
        discrepancy = Discrepancy(
            discrepancy_id="disc_1",
            page_url="https://example.com/login",
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            component_selector="button.submit",
            actual_content="Sign In",
            expected_content="Log In",
            guideline_chunk_id="chunk_1",
            guideline_section="sec_1",
            guideline_heading="Login Page",
            severity=SeverityLevel.WARNING,
            confidence_score=0.85,
            reason="Button text differs",
            screenshot_path="/data/screenshots/disc_1.png",
            remediation_suggestion="Change button text to 'Log In'",
            additional_context={"button_color": "blue"},
        )
        assert discrepancy.expected_content == "Log In"
        assert discrepancy.guideline_section == "sec_1"
        assert discrepancy.remediation_suggestion is not None
        assert discrepancy.additional_context["button_color"] == "blue"

    def test_discrepancy_confidence_validation(self):
        """Test Discrepancy confidence_score validation."""
        # Valid confidence scores
        for score in [0.0, 0.5, 1.0]:
            discrepancy = Discrepancy(
                discrepancy_id="disc_1",
                page_url="https://example.com",
                component_id="comp_1",
                component_type=ComponentType.TEXT,
                component_selector="p",
                actual_content="Text",
                guideline_chunk_id="chunk_1",
                severity=SeverityLevel.INFO,
                confidence_score=score,
                reason="Test",
            )
            assert discrepancy.confidence_score == score

        # Invalid confidence score
        with pytest.raises(ValueError):
            Discrepancy(
                discrepancy_id="disc_1",
                page_url="https://example.com",
                component_id="comp_1",
                component_type=ComponentType.TEXT,
                component_selector="p",
                actual_content="Text",
                guideline_chunk_id="chunk_1",
                severity=SeverityLevel.INFO,
                confidence_score=1.5,  # Invalid
                reason="Test",
            )

    def test_discrepancy_timestamp(self):
        """Test Discrepancy has auto-generated timestamp."""
        discrepancy = Discrepancy(
            discrepancy_id="disc_1",
            page_url="https://example.com",
            component_id="comp_1",
            component_type=ComponentType.TEXT,
            component_selector="p",
            actual_content="Text",
            guideline_chunk_id="chunk_1",
            severity=SeverityLevel.INFO,
            confidence_score=0.8,
            reason="Test",
        )
        assert discrepancy.detected_at is not None
        datetime.fromisoformat(discrepancy.detected_at)


class TestDiscrepancyReport:
    """Test DiscrepancyReport model."""

    def test_discrepancy_report_minimal(self):
        """Test creating DiscrepancyReport with minimal fields."""
        report = DiscrepancyReport(
            report_id="report_1",
            total_pages_checked=10,
            pages_with_discrepancies=3,
            total_discrepancies=5,
            overall_compliance=ComplianceStatus.PARTIAL,
            compliance_percentage=85.5,
            website_url="https://example.com",
            guideline_source="guidelines.pdf",
        )
        assert report.report_id == "report_1"
        assert report.total_pages_checked == 10
        assert report.pages_with_discrepancies == 3
        assert report.total_discrepancies == 5
        assert report.overall_compliance == ComplianceStatus.PARTIAL
        assert report.discrepancies == []

    def test_discrepancy_report_with_discrepancies(self):
        """Test DiscrepancyReport with discrepancies."""
        discrepancy = Discrepancy(
            discrepancy_id="disc_1",
            page_url="https://example.com",
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            component_selector="button",
            actual_content="Sign In",
            guideline_chunk_id="chunk_1",
            severity=SeverityLevel.WARNING,
            confidence_score=0.85,
            reason="Button text differs",
        )
        report = DiscrepancyReport(
            report_id="report_1",
            total_pages_checked=1,
            pages_with_discrepancies=1,
            total_discrepancies=1,
            overall_compliance=ComplianceStatus.NON_COMPLIANT,
            compliance_percentage=0.0,
            website_url="https://example.com",
            guideline_source="guidelines.pdf",
            discrepancies=[discrepancy],
            critical_count=0,
            warning_count=1,
            info_count=0,
            note_count=0,
        )
        assert len(report.discrepancies) == 1
        assert report.warning_count == 1

    def test_discrepancy_report_severity_breakdown(self):
        """Test DiscrepancyReport severity breakdown."""
        report = DiscrepancyReport(
            report_id="report_1",
            total_pages_checked=5,
            pages_with_discrepancies=3,
            total_discrepancies=5,
            overall_compliance=ComplianceStatus.PARTIAL,
            compliance_percentage=75.0,
            website_url="https://example.com",
            guideline_source="guidelines.pdf",
            critical_count=1,
            warning_count=2,
            info_count=1,
            note_count=1,
        )
        assert report.critical_count == 1
        assert report.warning_count == 2
        assert report.info_count == 1
        assert report.note_count == 1
        assert (
            report.critical_count
            + report.warning_count
            + report.info_count
            + report.note_count
        ) == report.total_discrepancies

    def test_discrepancy_report_timestamp(self):
        """Test DiscrepancyReport has auto-generated timestamp."""
        report = DiscrepancyReport(
            report_id="report_1",
            total_pages_checked=0,
            pages_with_discrepancies=0,
            total_discrepancies=0,
            overall_compliance=ComplianceStatus.COMPLIANT,
            compliance_percentage=100.0,
            website_url="https://example.com",
            guideline_source="guidelines.pdf",
        )
        assert report.generated_at is not None
        datetime.fromisoformat(report.generated_at)


class TestComparisonContext:
    """Test ComparisonContext model."""

    def test_comparison_context_creation(self):
        """Test creating ComparisonContext."""
        component = WebComponent(
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            selector="button",
            actual_text="Click",
        )
        chunk = GuidelineChunk(
            chunk_id="chunk_1",
            text="Button should say Click here",
            page_num=1,
            embedding=[0.1] * 1536,
        )
        context = ComparisonContext(
            component=component,
            relevant_guideline_chunks=[chunk],
            page_context="Login page with submit button",
            comparison_instructions="Check if button text matches guideline",
        )
        assert context.component.component_id == "comp_1"
        assert len(context.relevant_guideline_chunks) == 1
        assert context.page_context == "Login page with submit button"

    def test_comparison_context_multiple_chunks(self):
        """Test ComparisonContext with multiple guideline chunks."""
        component = WebComponent(
            component_id="comp_1",
            component_type=ComponentType.FORM,
            selector="form",
            actual_text="Form",
        )
        chunks = [
            GuidelineChunk(
                chunk_id=f"chunk_{i}",
                text=f"Guideline {i}",
                page_num=i,
                embedding=[0.1] * 1536,
            )
            for i in range(3)
        ]
        context = ComparisonContext(
            component=component,
            relevant_guideline_chunks=chunks,
            page_context="Multi-section form",
            comparison_instructions="Validate all sections",
        )
        assert len(context.relevant_guideline_chunks) == 3


class TestComparisonResult:
    """Test ComparisonResult model."""

    def test_comparison_result_compliant(self):
        """Test ComparisonResult for compliant component."""
        result = ComparisonResult(
            component_id="comp_1",
            compliant=True,
            confidence=0.95,
            reason="Component matches guideline",
            guideline_references=["chunk_1", "chunk_2"],
        )
        assert result.component_id == "comp_1"
        assert result.compliant is True
        assert result.confidence == 0.95
        assert len(result.guideline_references) == 2
        assert result.discrepancies == []

    def test_comparison_result_non_compliant(self):
        """Test ComparisonResult for non-compliant component."""
        result = ComparisonResult(
            component_id="comp_1",
            compliant=False,
            confidence=0.85,
            reason="Button text differs from guideline",
            discrepancies=["Text mismatch: 'Sign In' vs 'Log In'"],
            recommendations=["Update button text to match guideline"],
            guideline_references=["chunk_1"],
        )
        assert result.compliant is False
        assert len(result.discrepancies) == 1
        assert len(result.recommendations) == 1

    def test_comparison_result_confidence_validation(self):
        """Test ComparisonResult confidence validation."""
        for confidence in [0.0, 0.5, 1.0]:
            result = ComparisonResult(
                component_id="comp_1",
                compliant=True,
                confidence=confidence,
                reason="Test",
            )
            assert result.confidence == confidence


class TestPageStats:
    """Test PageStats model."""

    def test_page_stats_creation(self):
        """Test creating PageStats."""
        stats = PageStats(
            url="https://example.com/login",
            components_total=5,
            components_compliant=4,
            components_non_compliant=1,
            discrepancy_count=1,
            compliance_percentage=80.0,
        )
        assert stats.url == "https://example.com/login"
        assert stats.components_total == 5
        assert stats.components_compliant == 4
        assert stats.compliance_percentage == 80.0


class TestComponentStats:
    """Test ComponentStats model."""

    def test_component_stats_creation(self):
        """Test creating ComponentStats."""
        stats = ComponentStats(
            component_type=ComponentType.BUTTON,
            total=10,
            compliant=9,
            non_compliant=1,
            compliance_percentage=90.0,
        )
        assert stats.component_type == ComponentType.BUTTON
        assert stats.total == 10
        assert stats.compliant == 9
        assert stats.compliance_percentage == 90.0

    def test_component_stats_all_types(self):
        """Test ComponentStats for all component types."""
        for comp_type in ComponentType:
            stats = ComponentStats(
                component_type=comp_type,
                total=5,
                compliant=5,
                non_compliant=0,
                compliance_percentage=100.0,
            )
            assert stats.component_type == comp_type


class TestComplianceStats:
    """Test ComplianceStats model."""

    def test_compliance_stats_creation(self):
        """Test creating ComplianceStats."""
        stats = ComplianceStats(
            total_pages=10,
            compliant_pages=8,
            non_compliant_pages=2,
            total_components=50,
            compliant_components=45,
            total_discrepancies=5,
            compliance_percentage=90.0,
            by_severity={
                "critical": 0,
                "warning": 3,
                "info": 2,
                "note": 0,
            },
            by_component_type=[],
            by_page=[],
        )
        assert stats.total_pages == 10
        assert stats.compliant_pages == 8
        assert stats.compliance_percentage == 90.0

    def test_compliance_stats_with_breakdown(self):
        """Test ComplianceStats with detailed breakdown."""
        by_component = [
            ComponentStats(
                component_type=ComponentType.BUTTON,
                total=5,
                compliant=5,
                non_compliant=0,
                compliance_percentage=100.0,
            ),
            ComponentStats(
                component_type=ComponentType.FORM,
                total=3,
                compliant=2,
                non_compliant=1,
                compliance_percentage=66.7,
            ),
        ]
        by_page = [
            PageStats(
                url="https://example.com",
                components_total=5,
                components_compliant=5,
                components_non_compliant=0,
                discrepancy_count=0,
                compliance_percentage=100.0,
            ),
            PageStats(
                url="https://example.com/login",
                components_total=3,
                components_compliant=2,
                components_non_compliant=1,
                discrepancy_count=1,
                compliance_percentage=66.7,
            ),
        ]
        stats = ComplianceStats(
            total_pages=2,
            compliant_pages=1,
            non_compliant_pages=1,
            total_components=8,
            compliant_components=7,
            total_discrepancies=1,
            compliance_percentage=87.5,
            by_severity={"critical": 0, "warning": 1, "info": 0, "note": 0},
            by_component_type=by_component,
            by_page=by_page,
        )
        assert len(stats.by_component_type) == 2
        assert len(stats.by_page) == 2


class TestModelSerialization:
    """Test JSON serialization for all models."""

    def test_web_component_json_roundtrip(self):
        """Test WebComponent JSON roundtrip."""
        original = WebComponent(
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            selector="button",
            actual_text="Click",
        )
        json_data = original.dict()
        restored = WebComponent(**json_data)
        assert restored.component_id == original.component_id
        assert restored.component_type == original.component_type

    def test_discrepancy_json_roundtrip(self):
        """Test Discrepancy JSON roundtrip."""
        original = Discrepancy(
            discrepancy_id="disc_1",
            page_url="https://example.com",
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            component_selector="button",
            actual_content="Sign In",
            guideline_chunk_id="chunk_1",
            severity=SeverityLevel.WARNING,
            confidence_score=0.85,
            reason="Text differs",
        )
        json_data = original.dict()
        restored = Discrepancy(**json_data)
        assert restored.discrepancy_id == original.discrepancy_id
        assert restored.confidence_score == original.confidence_score

    def test_report_json_roundtrip(self):
        """Test DiscrepancyReport JSON roundtrip."""
        original = DiscrepancyReport(
            report_id="report_1",
            total_pages_checked=5,
            pages_with_discrepancies=2,
            total_discrepancies=3,
            overall_compliance=ComplianceStatus.PARTIAL,
            compliance_percentage=75.0,
            website_url="https://example.com",
            guideline_source="guidelines.pdf",
        )
        json_data = original.dict()
        restored = DiscrepancyReport(**json_data)
        assert restored.report_id == original.report_id
        assert restored.overall_compliance == original.overall_compliance


class TestModelValidation:
    """Test model validation and constraints."""

    def test_discrepancy_component_type_validation(self):
        """Test Discrepancy validates component type."""
        discrepancy = Discrepancy(
            discrepancy_id="disc_1",
            page_url="https://example.com",
            component_id="comp_1",
            component_type=ComponentType.LINK,
            component_selector="a",
            actual_content="Text",
            guideline_chunk_id="chunk_1",
            severity=SeverityLevel.INFO,
            confidence_score=0.8,
            reason="Test",
        )
        assert discrepancy.component_type == ComponentType.LINK

    def test_compliance_stats_percentages_valid(self):
        """Test ComplianceStats has valid percentages."""
        stats = ComplianceStats(
            total_pages=0,
            compliant_pages=0,
            non_compliant_pages=0,
            total_components=0,
            compliant_components=0,
            total_discrepancies=0,
            compliance_percentage=50.0,
            by_severity={},
            by_component_type=[],
            by_page=[],
        )
        assert 0.0 <= stats.compliance_percentage <= 100.0

    def test_page_stats_compliance_percentage_valid(self):
        """Test PageStats compliance percentage validation."""
        stats = PageStats(
            url="https://example.com",
            components_total=10,
            components_compliant=5,
            components_non_compliant=5,
            discrepancy_count=5,
            compliance_percentage=50.0,
        )
        assert 0.0 <= stats.compliance_percentage <= 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
