"""
Unit tests for coverage tracking system.

Tests coverage models, tracking, storage, and reporting functionality.
"""

import pytest
from datetime import datetime
from src.coverage.models import (
    PageStatus,
    FailureReason,
    PageCoverage,
    ExtractionCoverage,
    FailureLog,
    RetryAttempt,
    CoverageStatistics,
    CoverageReport,
    ExtractionCheckpoint,
    ExtractionProgress,
)
from src.coverage.tracker import CoverageTracker


class TestPageStatus:
    """Test PageStatus enum."""

    def test_page_status_values(self):
        """Test all PageStatus values."""
        assert PageStatus.SUCCESS.value == "success"
        assert PageStatus.FAILED.value == "failed"
        assert PageStatus.PARTIAL.value == "partial"
        assert PageStatus.SKIPPED.value == "skipped"
        assert PageStatus.RETRY.value == "retry"
        assert PageStatus.AUTH_FAILED.value == "auth_failed"
        assert PageStatus.TIMEOUT.value == "timeout"
        assert PageStatus.NOT_VISITED.value == "not_visited"


class TestFailureReason:
    """Test FailureReason enum."""

    def test_failure_reason_values(self):
        """Test all FailureReason values."""
        assert FailureReason.NETWORK_ERROR.value == "network_error"
        assert FailureReason.TIMEOUT.value == "timeout"
        assert FailureReason.LOGIN_FAILED.value == "login_failed"
        assert FailureReason.PAGE_NOT_FOUND.value == "page_not_found"
        assert FailureReason.ACCESS_DENIED.value == "access_denied"


class TestPageCoverage:
    """Test PageCoverage model."""

    def test_page_coverage_minimal(self):
        """Test creating PageCoverage with minimal fields."""
        coverage = PageCoverage(
            page_url="https://example.com/page1",
            page_id="page_1",
            status=PageStatus.SUCCESS,
            first_attempt_at=datetime.now().isoformat(),
            last_attempt_at=datetime.now().isoformat(),
        )
        assert coverage.page_url == "https://example.com/page1"
        assert coverage.page_id == "page_1"
        assert coverage.status == PageStatus.SUCCESS
        assert coverage.components_extracted == 0
        assert coverage.retry_count == 0

    def test_page_coverage_full(self):
        """Test creating PageCoverage with all fields."""
        coverage = PageCoverage(
            page_url="https://example.com/page1",
            page_id="page_1",
            status=PageStatus.SUCCESS,
            first_attempt_at=datetime.now().isoformat(),
            last_attempt_at=datetime.now().isoformat(),
            extraction_duration_seconds=5.2,
            components_extracted=10,
            components_failed=2,
            text_length_chars=5000,
            screenshot_taken=True,
            http_status_code=200,
            page_title="Page Title",
            retry_count=2,
            notes="Test notes",
        )
        assert coverage.extraction_duration_seconds == 5.2
        assert coverage.components_extracted == 10
        assert coverage.text_length_chars == 5000
        assert coverage.screenshot_taken is True
        assert coverage.http_status_code == 200


class TestExtractionCoverage:
    """Test ExtractionCoverage model."""

    def test_extraction_coverage_minimal(self):
        """Test creating ExtractionCoverage with minimal fields."""
        coverage = ExtractionCoverage(
            extraction_id="ext_1",
            website_url="https://example.com",
            total_pages_attempted=10,
            pages_successful=8,
            pages_failed=2,
            pages_partial=0,
            pages_skipped=0,
            pages_not_visited=0,
            coverage_percentage=100.0,
            success_percentage=80.0,
            total_components_targeted=50,
            total_components_extracted=45,
            total_components_failed=5,
            total_text_extracted_chars=50000,
            total_failures=2,
            total_retry_attempts=5,
            started_at=datetime.now().isoformat(),
        )
        assert coverage.extraction_id == "ext_1"
        assert coverage.pages_successful == 8
        assert coverage.coverage_percentage == 100.0

    def test_extraction_coverage_with_pages(self):
        """Test ExtractionCoverage with page details."""
        page = PageCoverage(
            page_url="https://example.com/page1",
            page_id="page_1",
            status=PageStatus.SUCCESS,
            first_attempt_at=datetime.now().isoformat(),
            last_attempt_at=datetime.now().isoformat(),
        )
        coverage = ExtractionCoverage(
            extraction_id="ext_1",
            website_url="https://example.com",
            total_pages_attempted=1,
            pages_successful=1,
            pages_failed=0,
            pages_partial=0,
            pages_skipped=0,
            pages_not_visited=0,
            coverage_percentage=100.0,
            success_percentage=100.0,
            total_components_targeted=5,
            total_components_extracted=5,
            total_components_failed=0,
            total_text_extracted_chars=5000,
            total_failures=0,
            total_retry_attempts=0,
            started_at=datetime.now().isoformat(),
            pages=[page],
        )
        assert len(coverage.pages) == 1
        assert coverage.pages[0].page_id == "page_1"

    def test_extraction_coverage_percentage_validation(self):
        """Test percentage validation."""
        # Valid percentages
        for pct in [0.0, 50.0, 100.0]:
            coverage = ExtractionCoverage(
                extraction_id="ext_1",
                website_url="https://example.com",
                total_pages_attempted=10,
                pages_successful=8,
                pages_failed=2,
                pages_partial=0,
                pages_skipped=0,
                pages_not_visited=0,
                coverage_percentage=pct,
                success_percentage=pct,
                total_components_targeted=50,
                total_components_extracted=45,
                total_components_failed=5,
                total_text_extracted_chars=50000,
                total_failures=2,
                total_retry_attempts=5,
                started_at=datetime.now().isoformat(),
            )
            assert coverage.coverage_percentage == pct

        # Invalid percentages
        with pytest.raises(ValueError):
            ExtractionCoverage(
                extraction_id="ext_1",
                website_url="https://example.com",
                total_pages_attempted=10,
                pages_successful=8,
                pages_failed=2,
                pages_partial=0,
                pages_skipped=0,
                pages_not_visited=0,
                coverage_percentage=150.0,  # Invalid
                success_percentage=80.0,
                total_components_targeted=50,
                total_components_extracted=45,
                total_components_failed=5,
                total_text_extracted_chars=50000,
                total_failures=2,
                total_retry_attempts=5,
                started_at=datetime.now().isoformat(),
            )


class TestFailureLog:
    """Test FailureLog model."""

    def test_failure_log_creation(self):
        """Test creating FailureLog."""
        failure = FailureLog(
            failure_id="fail_1",
            page_url="https://example.com/page1",
            page_id="page_1",
            reason=FailureReason.NETWORK_ERROR,
            message="Connection timeout",
            attempt_number=1,
            failed_at=datetime.now().isoformat(),
            duration_seconds=10.0,
        )
        assert failure.failure_id == "fail_1"
        assert failure.reason == FailureReason.NETWORK_ERROR
        assert failure.message == "Connection timeout"
        assert failure.recovered is False

    def test_failure_log_with_traceback(self):
        """Test FailureLog with exception details."""
        failure = FailureLog(
            failure_id="fail_1",
            page_url="https://example.com/page1",
            page_id="page_1",
            reason=FailureReason.PARSING_ERROR,
            message="Failed to parse HTML",
            exception_type="ParsingException",
            traceback="Traceback...",
            attempt_number=1,
            failed_at=datetime.now().isoformat(),
            duration_seconds=5.0,
            recovered=True,
            recovery_attempt=2,
        )
        assert failure.exception_type == "ParsingException"
        assert failure.recovered is True


class TestRetryAttempt:
    """Test RetryAttempt model."""

    def test_retry_attempt_creation(self):
        """Test creating RetryAttempt."""
        retry = RetryAttempt(
            retry_id="retry_1",
            page_url="https://example.com/page1",
            page_id="page_1",
            attempt_number=2,
            reason_for_retry="Network timeout on first attempt",
            previous_failure_reason=FailureReason.TIMEOUT,
            delay_seconds=5.0,
            backoff_multiplier=2.0,
            attempted_at=datetime.now().isoformat(),
            duration_seconds=0.0,
            succeeded=False,
        )
        assert retry.retry_id == "retry_1"
        assert retry.attempt_number == 2
        assert retry.delay_seconds == 5.0
        assert retry.succeeded is False

    def test_retry_attempt_success(self):
        """Test successful retry attempt."""
        retry = RetryAttempt(
            retry_id="retry_1",
            page_url="https://example.com/page1",
            page_id="page_1",
            attempt_number=2,
            reason_for_retry="Retry after timeout",
            previous_failure_reason=FailureReason.TIMEOUT,
            delay_seconds=5.0,
            backoff_multiplier=2.0,
            attempted_at=datetime.now().isoformat(),
            duration_seconds=3.5,
            succeeded=True,
            result_message="Successfully extracted",
            components_extracted=8,
            text_length_chars=4000,
        )
        assert retry.succeeded is True
        assert retry.components_extracted == 8


class TestCoverageCheckpoint:
    """Test ExtractionCheckpoint model."""

    def test_checkpoint_creation(self):
        """Test creating checkpoint."""
        checkpoint = ExtractionCheckpoint(
            checkpoint_id="chk_1",
            extraction_id="ext_1",
            created_at=datetime.now().isoformat(),
            checkpoint_number=1,
            pages_processed=5,
            pages_remaining=5,
            progress_percentage=50.0,
            components_extracted=20,
            text_chars_extracted=10000,
            failures_so_far=1,
            estimated_remaining_seconds=60.0,
        )
        assert checkpoint.checkpoint_number == 1
        assert checkpoint.progress_percentage == 50.0
        assert checkpoint.pages_processed == 5

    def test_checkpoint_with_eta(self):
        """Test checkpoint with ETA."""
        checkpoint = ExtractionCheckpoint(
            checkpoint_id="chk_1",
            extraction_id="ext_1",
            created_at=datetime.now().isoformat(),
            checkpoint_number=1,
            pages_processed=5,
            pages_remaining=5,
            progress_percentage=50.0,
            components_extracted=20,
            text_chars_extracted=10000,
            failures_so_far=1,
            estimated_remaining_seconds=300.0,
            estimated_completion_time=datetime.now().isoformat(),
        )
        assert checkpoint.estimated_remaining_seconds == 300.0
        assert checkpoint.estimated_completion_time is not None


class TestCoverageTracker:
    """Test CoverageTracker class."""

    def test_tracker_initialization(self):
        """Test tracker initialization."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        assert tracker.extraction_id == "ext_1"
        assert tracker.website_url == "https://example.com"
        assert tracker.total_pages == 10
        assert len(tracker.pages) == 0
        assert len(tracker.failures) == 0

    def test_tracker_start_page(self):
        """Test starting page extraction."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        tracker.start_page("https://example.com/page1", "page_1")
        
        assert "https://example.com/page1" in tracker.pages
        page = tracker.pages["https://example.com/page1"]
        assert page.status == PageStatus.RETRY
        assert page.page_id == "page_1"

    def test_tracker_succeed_page(self):
        """Test page success."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        tracker.start_page("https://example.com/page1", "page_1")
        tracker.succeed_page(
            "https://example.com/page1",
            components_count=5,
            text_length=2000,
            duration_seconds=2.0,
            title="Page 1",
        )
        
        page = tracker.pages["https://example.com/page1"]
        assert page.status == PageStatus.SUCCESS
        assert page.components_extracted == 5
        assert page.text_length_chars == 2000

    def test_tracker_fail_page(self):
        """Test page failure."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        tracker.start_page("https://example.com/page1", "page_1")
        tracker.fail_page(
            "https://example.com/page1",
            reason=FailureReason.NETWORK_ERROR,
            message="Connection failed",
            duration_seconds=5.0,
        )
        
        page = tracker.pages["https://example.com/page1"]
        assert page.status == PageStatus.FAILED
        assert page.failure_reason == FailureReason.NETWORK_ERROR
        assert len(tracker.failures) == 1

    def test_tracker_retry_page(self):
        """Test page retry."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        tracker.start_page("https://example.com/page1", "page_1")
        tracker.fail_page(
            "https://example.com/page1",
            reason=FailureReason.TIMEOUT,
            message="Timeout",
        )
        tracker.retry_page(
            "https://example.com/page1",
            reason="Retry after timeout",
            delay_seconds=5.0,
        )
        
        page = tracker.pages["https://example.com/page1"]
        assert len(page.retry_reasons) > 0  # Check retry reasons added
        assert len(tracker.retries) == 1

    def test_tracker_auth_tracking(self):
        """Test authentication tracking."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        
        tracker.auth_success()
        tracker.auth_success()
        tracker.auth_failure()
        
        assert tracker.successful_logins == 2
        assert tracker.auth_failures == 1

    def test_tracker_get_extraction_coverage(self):
        """Test getting extraction coverage."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        
        tracker.start_page("https://example.com/page1", "page_1")
        tracker.succeed_page("https://example.com/page1", components_count=5)
        
        tracker.start_page("https://example.com/page2", "page_2")
        tracker.fail_page("https://example.com/page2", reason=FailureReason.NETWORK_ERROR)
        
        coverage = tracker.get_extraction_coverage()
        assert coverage.extraction_id == "ext_1"
        assert coverage.pages_successful == 1
        assert coverage.pages_failed == 1
        assert coverage.total_pages_attempted == 2

    def test_tracker_skip_page(self):
        """Test skipping a page."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        tracker.skip_page("https://example.com/page1", reason="Invalid URL")
        
        page = tracker.pages["https://example.com/page1"]
        assert page.status == PageStatus.SKIPPED
        assert page.notes == "Invalid URL"

    def test_tracker_partial_page(self):
        """Test partial page extraction."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        tracker.start_page("https://example.com/page1", "page_1")
        tracker.partial_page(
            "https://example.com/page1",
            components_extracted=3,
            components_failed=2,
            text_length=1500,
        )
        
        page = tracker.pages["https://example.com/page1"]
        assert page.status == PageStatus.PARTIAL
        assert page.components_extracted == 3
        assert page.components_failed == 2

    def test_tracker_get_statistics(self):
        """Test getting tracker statistics."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        
        tracker.start_page("https://example.com/page1", "page_1")
        tracker.succeed_page("https://example.com/page1", components_count=5)
        
        stats = tracker.get_statistics()
        assert stats["extraction_id"] == "ext_1"
        assert stats["total_pages"] == 10
        assert stats["pages_visited"] == 1
        assert "pages_by_status" in stats

    def test_tracker_checkpoint_creation(self):
        """Test creating checkpoints."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        
        for i in range(5):
            tracker.start_page(f"https://example.com/page{i}", f"page_{i}")
            tracker.succeed_page(f"https://example.com/page{i}", components_count=5)
        
        checkpoint = tracker.create_checkpoint(1)
        assert checkpoint.checkpoint_number == 1
        assert checkpoint.pages_processed == 5
        assert checkpoint.progress_percentage > 0

    def test_tracker_get_failed_pages(self):
        """Test getting list of failed pages."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        
        tracker.start_page("https://example.com/page1", "page_1")
        tracker.fail_page("https://example.com/page1", reason=FailureReason.TIMEOUT)
        
        tracker.start_page("https://example.com/page2", "page_2")
        tracker.succeed_page("https://example.com/page2")
        
        failed = tracker.get_failed_pages()
        assert len(failed) == 1
        assert "https://example.com/page1" in failed

    def test_tracker_get_successful_pages(self):
        """Test getting list of successful pages."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        
        tracker.start_page("https://example.com/page1", "page_1")
        tracker.succeed_page("https://example.com/page1")
        
        tracker.start_page("https://example.com/page2", "page_2")
        tracker.fail_page("https://example.com/page2", reason=FailureReason.TIMEOUT)
        
        successful = tracker.get_successful_pages()
        assert len(successful) == 1
        assert "https://example.com/page1" in successful

    def test_tracker_failure_analysis(self):
        """Test failure analysis."""
        tracker = CoverageTracker("ext_1", "https://example.com", 10)
        
        tracker.start_page("https://example.com/page1", "page_1")
        tracker.fail_page("https://example.com/page1", reason=FailureReason.TIMEOUT)
        
        tracker.retry_page("https://example.com/page1", reason="Retry")
        tracker.complete_retry("https://example.com/page1", succeeded=True, duration_seconds=2.0)
        
        analysis = tracker.get_failure_analysis()
        assert analysis["total_failures"] == 1
        assert analysis["recovered"] == 1
        assert analysis["recovery_rate_percentage"] == 100.0


class TestCoverageStatistics:
    """Test CoverageStatistics model."""

    def test_coverage_statistics_creation(self):
        """Test creating CoverageStatistics."""
        stats = CoverageStatistics(
            extraction_id="ext_1",
            website_url="https://example.com",
            total_pages=10,
            covered_pages=8,
            uncovered_pages=2,
            coverage_percentage=80.0,
            total_component_types=5,
            total_components=45,
            total_text_chars=50000,
            average_chars_per_page=6250.0,
            total_failures=2,
            failure_rate_percentage=20.0,
            total_retries=5,
            successful_retries=3,
            retry_success_rate_percentage=60.0,
            authentication_attempts=2,
            authentication_success_rate_percentage=100.0,
            total_duration_seconds=120.0,
            average_page_duration_seconds=12.0,
            fastest_page_seconds=5.0,
            slowest_page_seconds=25.0,
        )
        assert stats.coverage_percentage == 80.0
        assert stats.total_pages == 10
        assert stats.failure_rate_percentage == 20.0


class TestCoverageReport:
    """Test CoverageReport model."""

    def test_coverage_report_creation(self):
        """Test creating CoverageReport."""
        stats = CoverageStatistics(
            extraction_id="ext_1",
            website_url="https://example.com",
            total_pages=10,
            covered_pages=8,
            uncovered_pages=2,
            coverage_percentage=80.0,
            total_component_types=5,
            total_components=45,
            total_text_chars=50000,
            average_chars_per_page=6250.0,
            total_failures=2,
            failure_rate_percentage=20.0,
            total_retries=5,
            successful_retries=3,
            retry_success_rate_percentage=60.0,
            authentication_attempts=2,
            authentication_success_rate_percentage=100.0,
            total_duration_seconds=120.0,
            average_page_duration_seconds=12.0,
            fastest_page_seconds=5.0,
            slowest_page_seconds=25.0,
        )
        
        report = CoverageReport(
            report_id="report_1",
            extraction_id="ext_1",
            website_url="https://example.com",
            title="Coverage Report",
            summary="Test summary",
            overall_coverage=stats,
            critical_issues=["High failure rate"],
            recommendations=["Investigate failures"],
        )
        assert report.report_id == "report_1"
        assert len(report.critical_issues) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
