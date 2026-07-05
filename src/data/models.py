"""
Canonical data models for compliance agent.

Defines all data structures used throughout the system for storing
extracted website data, guideline comparisons, and discrepancies.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, Field, validator


class ComponentType(str, Enum):
    """Types of web components."""

    TEXT = "text"
    HEADING = "heading"
    BUTTON = "button"
    LINK = "link"
    FORM = "form"
    INPUT = "input"
    IMAGE = "image"
    TABLE = "table"
    DROPDOWN = "dropdown"
    MODAL = "modal"
    ALERT = "alert"
    NAVIGATION = "navigation"
    CARD = "card"
    ICON = "icon"
    OTHER = "other"


class SeverityLevel(str, Enum):
    """Severity levels for discrepancies."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    NOTE = "note"


class ComplianceStatus(str, Enum):
    """Overall compliance status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class DiscrepancyType(str, Enum):
    """Types of discrepancies."""

    MISSING = "missing"
    EXTRA = "extra"
    INCORRECT = "incorrect"
    OTHER = "other"


# ============================================================================
# Web Component Models
# ============================================================================


class WebComponent(BaseModel):
    """Represents a single web component extracted from page."""

    component_id: str = Field(description="Unique component identifier")
    component_type: ComponentType = Field(description="Type of component")
    selector: str = Field(description="CSS selector to locate component")
    actual_text: Optional[str] = Field(default=None, description="Actual text content")
    actual_html: Optional[str] = Field(default=None, description="Actual HTML")
    attributes: Dict[str, str] = Field(
        default_factory=dict, description="HTML attributes"
    )
    position: Dict[str, int] = Field(
        default_factory=dict, description="Position on page (x, y, width, height)"
    )
    screenshot_path: Optional[str] = Field(
        default=None, description="Path to component screenshot"
    )

    class Config:
        use_enum_values = True


class WebPage(BaseModel):
    """Represents a single web page extracted."""

    page_id: str = Field(description="Unique page identifier")
    url: str = Field(description="Page URL")
    title: str = Field(description="Page title")
    description: Optional[str] = Field(default=None, description="Meta description")
    page_text: str = Field(description="Full page text content")
    components: List[WebComponent] = Field(
        default_factory=list, description="Extracted components"
    )
    screenshot_path: Optional[str] = Field(
        default=None, description="Full page screenshot"
    )
    extracted_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Extraction timestamp",
    )
    extraction_duration_seconds: float = Field(
        default=0.0, description="Time to extract page"
    )

    class Config:
        use_enum_values = True


class WebsiteExtraction(BaseModel):
    """Complete website extraction."""

    extraction_id: str = Field(description="Unique extraction identifier")
    website_url: str = Field(description="Root website URL")
    pages: List[WebPage] = Field(default_factory=list, description="Extracted pages")
    total_pages_extracted: int = Field(description="Total pages processed")
    total_pages_attempted: int = Field(description="Total pages attempted")
    extraction_errors: List[str] = Field(
        default_factory=list, description="Extraction errors"
    )
    started_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Extraction start time",
    )
    completed_at: Optional[str] = Field(
        default=None, description="Extraction completion time"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        use_enum_values = True


# ============================================================================
# Guideline Chunk Models
# ============================================================================


class GuidelineChunk(BaseModel):
    """Guideline chunk with metadata."""

    chunk_id: str = Field(description="Unique chunk identifier")
    text: str = Field(description="Chunk text content")
    page_num: int = Field(description="Source page number")
    section: Optional[str] = Field(default=None, description="Section identifier")
    heading: Optional[str] = Field(default=None, description="Section heading")
    embedding: List[float] = Field(description="Semantic embedding vector")

    class Config:
        use_enum_values = True


# ============================================================================
# Discrepancy Models
# ============================================================================


class Discrepancy(BaseModel):
    """Represents a single discrepancy between web content and guidelines."""

    discrepancy_id: str = Field(description="Unique discrepancy identifier")
    page_url: str = Field(description="Page URL where discrepancy found")
    component_id: str = Field(description="Component with discrepancy")
    component_type: ComponentType = Field(description="Type of component")
    component_selector: str = Field(description="CSS selector to locate")
    
    # Content comparison
    actual_content: str = Field(description="Actual content from website")
    expected_content: Optional[str] = Field(
        default=None, description="Expected content from guideline"
    )
    
    # Guideline reference
    guideline_chunk_id: str = Field(description="Referenced guideline chunk")
    guideline_section: Optional[str] = Field(
        default=None, description="Guideline section"
    )
    guideline_heading: Optional[str] = Field(
        default=None, description="Guideline heading"
    )
    
    # Severity and confidence
    severity: SeverityLevel = Field(description="Discrepancy severity")
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Confidence in discrepancy (0-1)"
    )
    
    # Evidence
    reason: str = Field(description="Why this is a discrepancy")
    screenshot_path: Optional[str] = Field(
        default=None, description="Screenshot showing discrepancy"
    )
    
    # Metadata
    detected_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Detection timestamp",
    )
    remediation_suggestion: Optional[str] = Field(
        default=None, description="How to fix"
    )
    additional_context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )

    @validator("confidence_score")
    def validate_confidence(cls, v):
        """Validate confidence score is between 0 and 1."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence_score must be between 0 and 1")
        return v

    class Config:
        use_enum_values = True


class DiscrepancyReport(BaseModel):
    """Report of all discrepancies found."""

    report_id: str = Field(description="Unique report identifier")
    
    # Summary
    total_pages_checked: int = Field(description="Total pages checked")
    pages_with_discrepancies: int = Field(description="Pages with issues")
    total_discrepancies: int = Field(description="Total discrepancies found")
    
    # Breakdown by severity
    critical_count: int = Field(default=0, description="Critical issues")
    warning_count: int = Field(default=0, description="Warnings")
    info_count: int = Field(default=0, description="Info messages")
    note_count: int = Field(default=0, description="Notes")
    
    # Compliance status
    overall_compliance: ComplianceStatus = Field(description="Overall status")
    compliance_percentage: float = Field(
        ge=0.0, le=100.0, description="Compliance percentage"
    )
    
    # Discrepancies
    discrepancies: List[Discrepancy] = Field(
        default_factory=list, description="List of discrepancies"
    )
    
    # Metadata
    generated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Report generation time",
    )
    website_url: str = Field(description="Website URL checked")
    guideline_source: str = Field(description="Guideline document source")
    analysis_duration_seconds: float = Field(
        default=0.0, description="Time to analyze"
    )
    additional_notes: Optional[str] = Field(
        default=None, description="Additional notes"
    )

    class Config:
        use_enum_values = True


# ============================================================================
# Comparison Context Models
# ============================================================================


class ComparisonContext(BaseModel):
    """Context for LLM-based comparison."""

    component: WebComponent = Field(description="Component being compared")
    relevant_guideline_chunks: List[GuidelineChunk] = Field(
        description="Relevant guideline chunks"
    )
    page_context: str = Field(description="Surrounding page context")
    comparison_instructions: str = Field(description="Instructions for comparison")

    class Config:
        use_enum_values = True


class ComparisonResult(BaseModel):
    """Result of component comparison."""

    component_id: str = Field(description="Component ID")
    compliant: bool = Field(description="Is component compliant?")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    reason: str = Field(description="Reason for decision")
    discrepancies: List[str] = Field(
        default_factory=list, description="List of issues found"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations"
    )
    guideline_references: List[str] = Field(
        default_factory=list, description="Referenced guideline chunks"
    )

    class Config:
        use_enum_values = True


# ============================================================================
# Summary Statistics Models
# ============================================================================


class PageStats(BaseModel):
    """Statistics for a page."""

    url: str = Field(description="Page URL")
    components_total: int = Field(description="Total components")
    components_compliant: int = Field(description="Compliant components")
    components_non_compliant: int = Field(description="Non-compliant components")
    discrepancy_count: int = Field(description="Discrepancies found")
    compliance_percentage: float = Field(description="Compliance percentage")

    class Config:
        use_enum_values = True


class ComponentStats(BaseModel):
    """Statistics by component type."""

    component_type: ComponentType = Field(description="Component type")
    total: int = Field(description="Total count")
    compliant: int = Field(description="Compliant count")
    non_compliant: int = Field(description="Non-compliant count")
    compliance_percentage: float = Field(description="Compliance percentage")

    class Config:
        use_enum_values = True


class ComplianceStats(BaseModel):
    """Overall compliance statistics."""

    total_pages: int = Field(description="Total pages")
    compliant_pages: int = Field(description="Compliant pages")
    non_compliant_pages: int = Field(description="Non-compliant pages")
    total_components: int = Field(description="Total components")
    compliant_components: int = Field(description="Compliant components")
    total_discrepancies: int = Field(description="Total discrepancies")
    compliance_percentage: float = Field(description="Overall compliance %")
    by_severity: Dict[str, int] = Field(description="Count by severity")
    by_component_type: List[ComponentStats] = Field(description="By component type")
    by_page: List[PageStats] = Field(description="By page")

    class Config:
        use_enum_values = True
