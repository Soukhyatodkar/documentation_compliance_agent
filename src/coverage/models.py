"""
Coverage tracking data models.

Defines all data structures used for tracking website extraction
progress, page visit statistics, and failure analysis.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator


class PageStatus(str, Enum):
    """Status of a page extraction."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    RETRY = "retry"
    AUTH_FAILED = "auth_failed"
    TIMEOUT = "timeout"
    NOT_VISITED = "not_visited"


class FailureReason(str, Enum):
    """Reasons for extraction failure."""

    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    LOGIN_FAILED = "login_failed"
    PAGE_NOT_FOUND = "page_not_found"
    ACCESS_DENIED = "access_denied"
    CONTENT_NOT_FOUND = "content_not_found"
    PARSING_ERROR = "parsing_error"
    BROWSER_CRASH = "browser_crash"
    UNKNOWN = "unknown"


# ============================================================================
# Page Coverage Models
# ============================================================================


class PageCoverage(BaseModel):
    """Coverage information for a single page."""

    page_url: str = Field(description="Page URL")
    page_id: str = Field(description="Page ID from extraction")
    status: PageStatus = Field(description="Current extraction status")
    
    # Timing
    first_attempt_at: str = Field(description="First attempt timestamp")
    last_attempt_at: str = Field(description="Last attempt timestamp")
    extraction_duration_seconds: float = Field(
        default=0.0, description="Time to extract page"
    )
    
    # Components
    components_extracted: int = Field(default=0, description="Components found")
    components_failed: int = Field(default=0, description="Components not extracted")
    
    # Content
    text_length_chars: int = Field(default=0, description="Length of extracted text")
    screenshot_taken: bool = Field(default=False, description="Screenshot captured")
    
    # Metadata
    http_status_code: Optional[int] = Field(
        default=None, description="HTTP status code"
    )
    page_title: Optional[str] = Field(default=None, description="Page title")
    page_url_redirect: Optional[str] = Field(
        default=None, description="Redirected URL if applicable"
    )
    
    # Failure info
    failure_reason: Optional[FailureReason] = Field(
        default=None, description="Reason for failure if failed"
    )
    failure_message: Optional[str] = Field(
        default=None, description="Detailed failure message"
    )
    
    # Recovery info
    recovered: bool = Field(default=False, description="Was this recovered on retry?")
    recovery_attempt: Optional[int] = Field(default=None, description="Which retry recovered this")
    
    # Retry tracking
    retry_count: int = Field(default=0, description="Number of retries")
    retry_reasons: List[str] = Field(default_factory=list, description="Retry reasons")
    
    # Status tracking
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp",
    )
    
    # Additional context
    notes: Optional[str] = Field(default=None, description="Additional notes")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        use_enum_values = True


class ExtractionCoverage(BaseModel):
    """Overall extraction coverage statistics."""

    extraction_id: str = Field(description="Extraction ID")
    website_url: str = Field(description="Website URL")
    
    # Pages
    total_pages_attempted: int = Field(description="Total pages attempted")
    pages_successful: int = Field(description="Successfully extracted pages")
    pages_failed: int = Field(description="Failed pages")
    pages_partial: int = Field(description="Partially extracted pages")
    pages_skipped: int = Field(description="Skipped pages")
    pages_not_visited: int = Field(description="Pages not visited")
    
    # Coverage percentage
    coverage_percentage: float = Field(ge=0.0, le=100.0, description="Coverage %")
    success_percentage: float = Field(ge=0.0, le=100.0, description="Success %")
    
    # Components
    total_components_targeted: int = Field(description="Target components")
    total_components_extracted: int = Field(description="Extracted components")
    total_components_failed: int = Field(description="Failed components")
    
    # Content
    total_text_extracted_chars: int = Field(description="Total text characters")
    total_images_captured: int = Field(default=0, description="Images captured")
    total_screenshots_taken: int = Field(default=0, description="Screenshots taken")
    
    # Failures and retries
    total_failures: int = Field(description="Total failures")
    total_retry_attempts: int = Field(description="Total retry attempts")
    failures_by_reason: Dict[str, int] = Field(
        default_factory=dict, description="Failures grouped by reason"
    )
    
    # Authentication
    authentication_failures: int = Field(default=0, description="Auth failures")
    successful_logins: int = Field(default=0, description="Successful logins")
    
    # Timing
    started_at: str = Field(description="Extraction start time")
    completed_at: Optional[str] = Field(default=None, description="Extraction completion time")
    total_duration_seconds: float = Field(
        default=0.0, description="Total extraction duration"
    )
    
    # Page coverage details
    pages: List[PageCoverage] = Field(
        default_factory=list, description="Per-page coverage details"
    )

    @validator("coverage_percentage", "success_percentage")
    def validate_percentage(cls, v):
        """Validate percentage is between 0 and 100."""
        if not (0.0 <= v <= 100.0):
            raise ValueError("Percentage must be between 0 and 100")
        return v

    class Config:
        use_enum_values = True


# ============================================================================
# Failure and Retry Models
# ============================================================================


class FailureLog(BaseModel):
    """Log entry for a failed extraction attempt."""

    failure_id: str = Field(description="Unique failure identifier")
    page_url: str = Field(description="Page URL that failed")
    page_id: Optional[str] = Field(default=None, description="Page ID if available")
    
    # Failure details
    reason: FailureReason = Field(description="Failure reason")
    message: str = Field(description="Error message")
    exception_type: Optional[str] = Field(default=None, description="Exception class name")
    traceback: Optional[str] = Field(default=None, description="Full traceback")
    
    # Context
    attempt_number: int = Field(description="Which attempt failed")
    components_extracted_before_failure: int = Field(
        default=0, description="Components extracted before failure"
    )
    
    # Timing
    failed_at: str = Field(description="Failure timestamp")
    duration_seconds: float = Field(description="Duration before failure")
    
    # Recovery info
    recovered: bool = Field(default=False, description="Was this recovered on retry?")
    recovery_attempt: Optional[int] = Field(default=None, description="Which retry recovered this")

    class Config:
        use_enum_values = True


class RetryAttempt(BaseModel):
    """Log entry for a retry attempt."""

    retry_id: str = Field(description="Unique retry identifier")
    page_url: str = Field(description="Page URL being retried")
    page_id: Optional[str] = Field(default=None, description="Page ID if available")
    
    # Retry details
    attempt_number: int = Field(description="Attempt number (1-based)")
    reason_for_retry: str = Field(description="Why retry was triggered")
    previous_failure_reason: Optional[FailureReason] = Field(
        default=None, description="What failed before"
    )
    
    # Retry configuration
    delay_seconds: float = Field(description="Delay before retry")
    backoff_multiplier: float = Field(description="Backoff multiplier used")
    
    # Timing
    attempted_at: str = Field(description="Retry attempt timestamp")
    duration_seconds: float = Field(description="Duration of retry attempt")
    
    # Result
    succeeded: bool = Field(description="Did retry succeed?")
    result_message: Optional[str] = Field(default=None, description="Result message")
    
    # Components on retry
    components_extracted: int = Field(default=0, description="Components extracted")
    text_length_chars: int = Field(default=0, description="Text extracted")

    class Config:
        use_enum_values = True


# ============================================================================
# Aggregated Statistics Models
# ============================================================================


class CoverageStatistics(BaseModel):
    """Aggregated coverage statistics."""

    extraction_id: str = Field(description="Extraction ID")
    website_url: str = Field(description="Website URL")
    
    # Overall metrics
    total_pages: int = Field(description="Total pages tracked")
    covered_pages: int = Field(description="Pages with successful extraction")
    uncovered_pages: int = Field(description="Pages not covered")
    coverage_percentage: float = Field(ge=0.0, le=100.0, description="Coverage %")
    
    # Component extraction
    total_component_types: int = Field(description="Unique component types")
    total_components: int = Field(description="Total components extracted")
    components_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Count by component type"
    )
    
    # Content metrics
    total_text_chars: int = Field(description="Total characters extracted")
    average_chars_per_page: float = Field(description="Average chars per page")
    total_images: int = Field(default=0, description="Total images captured")
    
    # Failure analysis
    total_failures: int = Field(description="Total failures")
    failure_rate_percentage: float = Field(ge=0.0, le=100.0, description="Failure %")
    top_failure_reasons: List[str] = Field(
        default_factory=list, description="Top failure reasons"
    )
    
    # Retry statistics
    total_retries: int = Field(description="Total retry attempts")
    successful_retries: int = Field(description="Successful retries")
    retry_success_rate_percentage: float = Field(
        ge=0.0, le=100.0, description="Retry success %"
    )
    
    # Authentication
    authentication_attempts: int = Field(default=0, description="Auth attempts")
    authentication_success_rate_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Auth success %"
    )
    
    # Timing
    total_duration_seconds: float = Field(description="Total extraction time")
    average_page_duration_seconds: float = Field(description="Average per page")
    fastest_page_seconds: float = Field(description="Fastest page")
    slowest_page_seconds: float = Field(description="Slowest page")
    
    # Status breakdown
    pages_by_status: Dict[str, int] = Field(
        default_factory=dict, description="Pages grouped by status"
    )

    @validator(
        "coverage_percentage",
        "failure_rate_percentage",
        "retry_success_rate_percentage",
        "authentication_success_rate_percentage",
    )
    def validate_percentage(cls, v):
        """Validate percentage is between 0 and 100."""
        if not (0.0 <= v <= 100.0):
            raise ValueError("Percentage must be between 0 and 100")
        return v

    class Config:
        use_enum_values = True


class CoverageReport(BaseModel):
    """Complete coverage report."""

    report_id: str = Field(description="Unique report identifier")
    extraction_id: str = Field(description="Associated extraction ID")
    website_url: str = Field(description="Website URL")
    
    # Summary
    title: str = Field(description="Report title")
    summary: str = Field(description="Executive summary")
    
    # Statistics
    overall_coverage: CoverageStatistics = Field(description="Overall statistics")
    
    # Details
    covered_pages: List[str] = Field(default_factory=list, description="Covered page URLs")
    uncovered_pages: List[str] = Field(default_factory=list, description="Uncovered page URLs")
    failed_pages: List[str] = Field(default_factory=list, description="Failed page URLs")
    
    # Key findings
    critical_issues: List[str] = Field(
        default_factory=list, description="Critical issues found"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations"
    )
    
    # Timing
    generated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Report generation time",
    )
    
    # Additional
    notes: Optional[str] = Field(default=None, description="Additional notes")
    next_steps: Optional[str] = Field(default=None, description="Recommended next steps")

    class Config:
        use_enum_values = True


# ============================================================================
# Checkpoint and Progress Models
# ============================================================================


class ExtractionCheckpoint(BaseModel):
    """Checkpoint snapshot during extraction."""

    checkpoint_id: str = Field(description="Unique checkpoint identifier")
    extraction_id: str = Field(description="Extraction ID")
    
    # Timing
    created_at: str = Field(description="Checkpoint timestamp")
    checkpoint_number: int = Field(description="Sequential checkpoint number")
    
    # Progress
    pages_processed: int = Field(description="Pages processed so far")
    pages_remaining: int = Field(description="Pages remaining")
    progress_percentage: float = Field(ge=0.0, le=100.0, description="Progress %")
    
    # Current state
    current_page_url: Optional[str] = Field(default=None, description="Currently processing page")
    current_page_status: Optional[PageStatus] = Field(default=None, description="Current page status")
    
    # Statistics so far
    components_extracted: int = Field(description="Components extracted")
    text_chars_extracted: int = Field(description="Characters extracted")
    failures_so_far: int = Field(description="Failures so far")
    
    # ETA
    estimated_remaining_seconds: float = Field(description="Estimated time remaining")
    estimated_completion_time: Optional[str] = Field(default=None, description="Estimated completion")

    @validator("progress_percentage")
    def validate_progress(cls, v):
        """Validate progress percentage."""
        if not (0.0 <= v <= 100.0):
            raise ValueError("Progress must be between 0 and 100")
        return v

    class Config:
        use_enum_values = True


class ExtractionProgress(BaseModel):
    """Overall extraction progress tracking."""

    extraction_id: str = Field(description="Extraction ID")
    website_url: str = Field(description="Website URL")
    
    # Timeline
    started_at: str = Field(description="Start time")
    current_checkpoint_id: str = Field(description="Latest checkpoint ID")
    
    # Progress
    progress_percentage: float = Field(ge=0.0, le=100.0, description="Progress %")
    pages_processed: int = Field(description="Pages processed")
    pages_total: int = Field(description="Total pages")
    
    # Performance
    current_speed_pages_per_minute: float = Field(description="Processing speed")
    estimated_completion_time: str = Field(description="Estimated completion")
    
    # Status
    is_active: bool = Field(description="Is extraction currently running?")
    is_paused: bool = Field(description="Is extraction paused?")
    pause_reason: Optional[str] = Field(description="Reason for pause if paused")
    
    # Checkpoints
    checkpoints: List[ExtractionCheckpoint] = Field(
        default_factory=list, description="All checkpoints"
    )
    
    # Latest statistics
    last_update_at: str = Field(description="Last update timestamp")
    latest_error: Optional[str] = Field(description="Latest error if any")

    @validator("progress_percentage")
    def validate_progress(cls, v):
        """Validate progress percentage."""
        if not (0.0 <= v <= 100.0):
            raise ValueError("Progress must be between 0 and 100")
        return v

    class Config:
        use_enum_values = True
