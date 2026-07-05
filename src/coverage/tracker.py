"""
Coverage tracking system.

Tracks website extraction progress, page visits, failures,
and retry attempts throughout the extraction pipeline.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from src.coverage.models import (
    PageStatus,
    FailureReason,
    PageCoverage,
    ExtractionCoverage,
    FailureLog,
    RetryAttempt,
    CoverageStatistics,
    ExtractionCheckpoint,
    ExtractionProgress,
)
from src.core.exceptions import ValidationError
from src.utils.helpers import DictHelper


logger = logging.getLogger(__name__)


class CoverageTracker:
    """Tracks coverage of website extraction."""

    def __init__(self, extraction_id: str, website_url: str, total_pages: int):
        """Initialize coverage tracker."""
        self.extraction_id = extraction_id
        self.website_url = website_url
        self.total_pages = total_pages
        
        # Initialize tracking data
        self.pages: Dict[str, PageCoverage] = {}
        self.failures: List[FailureLog] = []
        self.retries: List[RetryAttempt] = []
        self.checkpoints: List[ExtractionCheckpoint] = []
        
        # Statistics
        self.started_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        
        # Current state
        self.current_page_url: Optional[str] = None
        self.total_components_extracted = 0
        self.total_text_chars = 0
        self.successful_logins = 0
        self.auth_failures = 0
        
        logger.info(
            f"Initialized coverage tracker for {extraction_id} "
            f"({website_url}, {total_pages} pages)"
        )

    def start_page(self, page_url: str, page_id: str) -> None:
        """Mark page as started extraction."""
        if page_url not in self.pages:
            self.pages[page_url] = PageCoverage(
                page_url=page_url,
                page_id=page_id,
                status=PageStatus.RETRY,  # Initial status
                first_attempt_at=datetime.now().isoformat(),
                last_attempt_at=datetime.now().isoformat(),
            )
        else:
            page = self.pages[page_url]
            page.last_attempt_at = datetime.now().isoformat()
            page.retry_count += 1
        
        self.current_page_url = page_url
        logger.debug(f"Started extraction for page: {page_url}")

    def succeed_page(
        self,
        page_url: str,
        components_count: int = 0,
        text_length: int = 0,
        duration_seconds: float = 0.0,
        title: Optional[str] = None,
        http_status: Optional[int] = None,
        screenshot_taken: bool = False,
    ) -> None:
        """Mark page as successfully extracted."""
        if page_url not in self.pages:
            logger.warning(f"Page {page_url} not started, creating entry")
            self.start_page(page_url, f"page_{len(self.pages)}")
        
        page = self.pages[page_url]
        page.status = PageStatus.SUCCESS
        page.components_extracted = components_count
        page.text_length_chars = text_length
        page.extraction_duration_seconds = duration_seconds
        page.page_title = title
        page.http_status_code = http_status
        page.screenshot_taken = screenshot_taken
        page.last_attempt_at = datetime.now().isoformat()
        
        # Update totals
        self.total_components_extracted += components_count
        self.total_text_chars += text_length
        
        logger.info(f"Page succeeded: {page_url} ({components_count} components)")

    def fail_page(
        self,
        page_url: str,
        reason: FailureReason,
        message: str = "",
        exception_type: Optional[str] = None,
        traceback_text: Optional[str] = None,
        duration_seconds: float = 0.0,
        components_before_failure: int = 0,
    ) -> None:
        """Mark page as failed extraction."""
        if page_url not in self.pages:
            logger.warning(f"Page {page_url} not started, creating entry")
            self.start_page(page_url, f"page_{len(self.pages)}")
        
        page = self.pages[page_url]
        page.status = PageStatus.FAILED
        page.failure_reason = reason
        page.failure_message = message
        page.last_attempt_at = datetime.now().isoformat()
        page.components_failed = components_before_failure
        
        # Create failure log
        failure_id = f"fail_{len(self.failures)}"
        failure = FailureLog(
            failure_id=failure_id,
            page_url=page_url,
            page_id=page.page_id,
            reason=reason,
            message=message,
            exception_type=exception_type,
            traceback=traceback_text,
            attempt_number=page.retry_count + 1,
            components_extracted_before_failure=components_before_failure,
            failed_at=datetime.now().isoformat(),
            duration_seconds=duration_seconds,
        )
        self.failures.append(failure)
        
        logger.warning(f"Page failed: {page_url} (reason: {reason.value})")

    def retry_page(
        self,
        page_url: str,
        reason: str,
        delay_seconds: float = 0.0,
        backoff_multiplier: float = 1.0,
    ) -> None:
        """Log retry attempt for page."""
        if page_url not in self.pages:
            logger.warning(f"Page {page_url} not started, creating entry")
            self.start_page(page_url, f"page_{len(self.pages)}")
        
        page = self.pages[page_url]
        
        retry_id = f"retry_{len(self.retries)}"
        retry = RetryAttempt(
            retry_id=retry_id,
            page_url=page_url,
            page_id=page.page_id,
            attempt_number=page.retry_count + 1,
            reason_for_retry=reason,
            previous_failure_reason=page.failure_reason,
            delay_seconds=delay_seconds,
            backoff_multiplier=backoff_multiplier,
            attempted_at=datetime.now().isoformat(),
            duration_seconds=0.0,  # Will be updated if retry succeeds
            succeeded=False,
        )
        self.retries.append(retry)
        page.retry_reasons.append(reason)
        
        logger.info(f"Retry scheduled for page: {page_url} (attempt: {len(page.retry_reasons)})")

    def complete_retry(
        self,
        page_url: str,
        succeeded: bool,
        duration_seconds: float,
        components_extracted: int = 0,
        text_length: int = 0,
        result_message: Optional[str] = None,
    ) -> None:
        """Mark retry attempt as completed."""
        if not self.retries:
            logger.warning(f"No retries to complete for {page_url}")
            return
        
        # Find latest retry for this page
        for i in range(len(self.retries) - 1, -1, -1):
            if self.retries[i].page_url == page_url:
                retry = self.retries[i]
                retry.succeeded = succeeded
                retry.duration_seconds = duration_seconds
                retry.components_extracted = components_extracted
                retry.text_length_chars = text_length
                retry.result_message = result_message
                
                # If retry succeeded, mark page as recovered
                if succeeded and page_url in self.pages:
                    failure = next(
                        (f for f in self.failures if f.page_url == page_url),
                        None,
                    )
                    if failure:
                        failure.recovered = True
                        failure.recovery_attempt = retry.attempt_number
                
                logger.info(
                    f"Retry completed for page: {page_url} "
                    f"(succeeded: {succeeded})"
                )
                break

    def partial_page(
        self,
        page_url: str,
        components_extracted: int,
        components_failed: int,
        text_length: int = 0,
        duration_seconds: float = 0.0,
    ) -> None:
        """Mark page as partially extracted."""
        if page_url not in self.pages:
            logger.warning(f"Page {page_url} not started, creating entry")
            self.start_page(page_url, f"page_{len(self.pages)}")
        
        page = self.pages[page_url]
        page.status = PageStatus.PARTIAL
        page.components_extracted = components_extracted
        page.components_failed = components_failed
        page.text_length_chars = text_length
        page.extraction_duration_seconds = duration_seconds
        page.last_attempt_at = datetime.now().isoformat()
        
        self.total_components_extracted += components_extracted
        self.total_text_chars += text_length
        
        logger.info(
            f"Page partial: {page_url} "
            f"({components_extracted} extracted, {components_failed} failed)"
        )

    def skip_page(self, page_url: str, reason: str = "") -> None:
        """Mark page as skipped."""
        if page_url not in self.pages:
            self.pages[page_url] = PageCoverage(
                page_url=page_url,
                page_id=f"page_skipped_{len(self.pages)}",
                status=PageStatus.SKIPPED,
                first_attempt_at=datetime.now().isoformat(),
                last_attempt_at=datetime.now().isoformat(),
            )
        
        page = self.pages[page_url]
        page.status = PageStatus.SKIPPED
        page.notes = reason
        
        logger.info(f"Page skipped: {page_url} ({reason})")

    def auth_success(self) -> None:
        """Record successful authentication."""
        self.successful_logins += 1
        logger.info(f"Authentication successful (total: {self.successful_logins})")

    def auth_failure(self) -> None:
        """Record authentication failure."""
        self.auth_failures += 1
        logger.warning(f"Authentication failed (total: {self.auth_failures})")

    def add_components_extracted(self, count: int) -> None:
        """Add to components extracted count."""
        self.total_components_extracted += count

    def add_text_extracted(self, chars: int) -> None:
        """Add to text characters extracted."""
        self.total_text_chars += chars

    def create_checkpoint(self, checkpoint_number: int) -> ExtractionCheckpoint:
        """Create a checkpoint snapshot."""
        pages_processed = len([p for p in self.pages.values() if p.status != PageStatus.NOT_VISITED])
        pages_remaining = self.total_pages - pages_processed
        progress_pct = (pages_processed / self.total_pages * 100) if self.total_pages > 0 else 0
        
        # Calculate ETA
        elapsed = datetime.now() - self.started_at
        if pages_processed > 0:
            avg_time_per_page = elapsed.total_seconds() / pages_processed
            estimated_remaining = avg_time_per_page * pages_remaining
        else:
            estimated_remaining = 0
        
        checkpoint_id = f"chk_{checkpoint_number}"
        checkpoint = ExtractionCheckpoint(
            checkpoint_id=checkpoint_id,
            extraction_id=self.extraction_id,
            created_at=datetime.now().isoformat(),
            checkpoint_number=checkpoint_number,
            pages_processed=pages_processed,
            pages_remaining=pages_remaining,
            progress_percentage=progress_pct,
            current_page_url=self.current_page_url,
            current_page_status=self.pages.get(self.current_page_url, {}).status
            if self.current_page_url and self.current_page_url in self.pages
            else None,
            components_extracted=self.total_components_extracted,
            text_chars_extracted=self.total_text_chars,
            failures_so_far=len([p for p in self.pages.values() if p.status == PageStatus.FAILED]),
            estimated_remaining_seconds=estimated_remaining,
            estimated_completion_time=(
                (datetime.now() + timedelta(seconds=estimated_remaining)).isoformat()
                if estimated_remaining > 0
                else None
            ),
        )
        self.checkpoints.append(checkpoint)
        logger.info(f"Created checkpoint {checkpoint_number}: {progress_pct:.1f}% complete")
        return checkpoint

    def get_extraction_coverage(self) -> ExtractionCoverage:
        """Get overall extraction coverage statistics."""
        # Count pages by status
        successful = len([p for p in self.pages.values() if p.status == PageStatus.SUCCESS])
        failed = len([p for p in self.pages.values() if p.status == PageStatus.FAILED])
        partial = len([p for p in self.pages.values() if p.status == PageStatus.PARTIAL])
        skipped = len([p for p in self.pages.values() if p.status == PageStatus.SKIPPED])
        not_visited = self.total_pages - len(self.pages)
        
        total_visited = len(self.pages)
        coverage_pct = (total_visited / self.total_pages * 100) if self.total_pages > 0 else 0
        success_pct = (successful / total_visited * 100) if total_visited > 0 else 0
        
        # Count failures by reason
        failures_by_reason = defaultdict(int)
        for failure in self.failures:
            reason_key = failure.reason.value if isinstance(failure.reason, FailureReason) else str(failure.reason)
            failures_by_reason[reason_key] += 1
        
        # Count pages by status
        pages_by_status = defaultdict(int)
        for page in self.pages.values():
            status_key = page.status.value if isinstance(page.status, PageStatus) else str(page.status)
            pages_by_status[status_key] += 1
        
        total_duration = (datetime.now() - self.started_at).total_seconds()
        
        # Count components
        total_components_targeted = len(self.pages) * 5  # Estimate: 5 per page
        total_components_extracted = self.total_components_extracted
        total_components_failed = total_components_targeted - total_components_extracted
        
        return ExtractionCoverage(
            extraction_id=self.extraction_id,
            website_url=self.website_url,
            total_pages_attempted=total_visited,
            pages_successful=successful,
            pages_failed=failed,
            pages_partial=partial,
            pages_skipped=skipped,
            pages_not_visited=not_visited,
            coverage_percentage=coverage_pct,
            success_percentage=success_pct,
            total_components_targeted=total_components_targeted,
            total_components_extracted=total_components_extracted,
            total_components_failed=total_components_failed,
            total_text_extracted_chars=self.total_text_chars,
            total_failures=len(self.failures),
            total_retry_attempts=len(self.retries),
            failures_by_reason=dict(failures_by_reason),
            authentication_failures=self.auth_failures,
            successful_logins=self.successful_logins,
            started_at=self.started_at.isoformat(),
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            total_duration_seconds=total_duration,
            pages=list(self.pages.values()),
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get coverage statistics as dictionary."""
        coverage = self.get_extraction_coverage()
        
        # Calculate retry success rate
        successful_retries = len([r for r in self.retries if r.succeeded])
        retry_success_pct = (
            (successful_retries / len(self.retries) * 100) if self.retries else 0
        )
        
        # Calculate auth success rate
        total_auth_attempts = self.successful_logins + self.auth_failures
        auth_success_pct = (
            (self.successful_logins / total_auth_attempts * 100) if total_auth_attempts > 0 else 0
        )
        
        return {
            "extraction_id": self.extraction_id,
            "website_url": self.website_url,
            "total_pages": self.total_pages,
            "pages_visited": len(self.pages),
            "coverage_percentage": coverage.coverage_percentage,
            "success_percentage": coverage.success_percentage,
            "pages_by_status": {
                "success": coverage.pages_successful,
                "failed": coverage.pages_failed,
                "partial": coverage.pages_partial,
                "skipped": coverage.pages_skipped,
                "not_visited": coverage.pages_not_visited,
            },
            "components": {
                "total_targeted": coverage.total_components_targeted,
                "total_extracted": coverage.total_components_extracted,
                "total_failed": coverage.total_components_failed,
            },
            "content": {
                "total_text_chars": coverage.total_text_extracted_chars,
                "average_chars_per_page": (
                    coverage.total_text_extracted_chars / len(self.pages)
                    if self.pages
                    else 0
                ),
            },
            "failures": {
                "total": len(self.failures),
                "by_reason": coverage.failures_by_reason,
            },
            "retries": {
                "total_attempts": len(self.retries),
                "successful": successful_retries,
                "success_rate_percentage": retry_success_pct,
            },
            "authentication": {
                "successful_logins": self.successful_logins,
                "failures": self.auth_failures,
                "success_rate_percentage": auth_success_pct,
            },
            "timing": {
                "started_at": coverage.started_at,
                "completed_at": coverage.completed_at,
                "total_duration_seconds": coverage.total_duration_seconds,
            },
        }

    def mark_complete(self) -> None:
        """Mark extraction as completed."""
        self.completed_at = datetime.now()
        logger.info(f"Extraction marked complete: {self.extraction_id}")

    def get_failed_pages(self) -> List[str]:
        """Get list of failed page URLs."""
        return [p.page_url for p in self.pages.values() if p.status == PageStatus.FAILED]

    def get_successful_pages(self) -> List[str]:
        """Get list of successful page URLs."""
        return [p.page_url for p in self.pages.values() if p.status == PageStatus.SUCCESS]

    def get_uncovered_pages(self) -> List[str]:
        """Get list of pages not visited."""
        visited_urls = set(self.pages.keys())
        # This would need a complete list of all pages to compare against
        # For now, just return not_visited count
        return []

    def get_page_coverage(self, page_url: str) -> Optional[PageCoverage]:
        """Get coverage for specific page."""
        return self.pages.get(page_url)

    def get_failure_analysis(self) -> Dict[str, Any]:
        """Get detailed failure analysis."""
        recovered_failures = len([f for f in self.failures if f.recovered])
        unrecovered_failures = len(self.failures) - recovered_failures
        
        return {
            "total_failures": len(self.failures),
            "recovered": recovered_failures,
            "unrecovered": unrecovered_failures,
            "recovery_rate_percentage": (
                (recovered_failures / len(self.failures) * 100) if self.failures else 0
            ),
            "top_failure_reasons": self._get_top_failure_reasons(),
            "pages_with_most_failures": self._get_pages_with_most_failures(),
        }

    def _get_top_failure_reasons(self) -> List[tuple]:
        """Get top failure reasons."""
        reason_counts = defaultdict(int)
        for failure in self.failures:
            reason_key = failure.reason.value if isinstance(failure.reason, FailureReason) else str(failure.reason)
            reason_counts[reason_key] += 1
        
        return sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    def _get_pages_with_most_failures(self) -> List[tuple]:
        """Get pages with most failures."""
        page_failure_counts = defaultdict(int)
        for failure in self.failures:
            page_failure_counts[failure.page_url] += 1
        
        return sorted(page_failure_counts.items(), key=lambda x: x[1], reverse=True)[:5]
