"""
Coverage reporting system.

Generates comprehensive coverage reports from coverage tracking data.
Provides summary statistics, analysis, and recommendations.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import defaultdict

from src.coverage.models import (
    CoverageReport,
    CoverageStatistics,
    PageStatus,
    FailureReason,
)
from src.coverage.tracker import CoverageTracker
from src.coverage.storage import (
    ExtractionCoverageStorage,
    FailureLogStorage,
    RetryStorage,
    CoverageQuery,
)


logger = logging.getLogger(__name__)


class CoverageReporter:
    """Generates coverage reports."""

    def __init__(
        self,
        tracker: CoverageTracker,
        coverage_storage: Optional[ExtractionCoverageStorage] = None,
        failure_storage: Optional[FailureLogStorage] = None,
        retry_storage: Optional[RetryStorage] = None,
    ):
        """Initialize coverage reporter."""
        self.tracker = tracker
        self.coverage_storage = coverage_storage
        self.failure_storage = failure_storage
        self.retry_storage = retry_storage
        logger.info(f"Initialized coverage reporter for {tracker.extraction_id}")

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate executive summary of coverage."""
        coverage = self.tracker.get_extraction_coverage()
        failure_analysis = self.tracker.get_failure_analysis()
        
        # Determine key findings
        critical_issues = []
        if coverage.pages_failed > 0:
            critical_issues.append(
                f"{coverage.pages_failed} pages failed extraction "
                f"({coverage.total_pages_attempted - coverage.pages_successful} total non-successful)"
            )
        
        if failure_analysis["recovery_rate_percentage"] < 50:
            critical_issues.append(
                "Low failure recovery rate "
                f"({failure_analysis['recovery_rate_percentage']:.1f}%)"
            )
        
        if coverage.coverage_percentage < 80:
            critical_issues.append(
                f"Coverage below target: {coverage.coverage_percentage:.1f}%"
            )
        
        # Recommendations
        recommendations = []
        if coverage.pages_failed > 0:
            recommendations.append("Investigate and fix pages with failed extractions")
        
        if len(failure_analysis["top_failure_reasons"]) > 0:
            top_reason = failure_analysis["top_failure_reasons"][0]
            recommendations.append(f"Address most common failure reason: {top_reason[0]}")
        
        if coverage.pages_not_visited > 0:
            recommendations.append(f"Ensure all {coverage.pages_not_visited} unvisited pages are accessible")
        
        return {
            "extraction_id": coverage.extraction_id,
            "website_url": coverage.website_url,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_pages": coverage.total_pages_attempted,
                "coverage_percentage": coverage.coverage_percentage,
                "success_percentage": coverage.success_percentage,
                "components_extracted": coverage.total_components_extracted,
                "total_failures": coverage.total_failures,
                "total_retries": coverage.total_retry_attempts,
            },
            "status_breakdown": {
                "successful": coverage.pages_successful,
                "failed": coverage.pages_failed,
                "partial": coverage.pages_partial,
                "skipped": coverage.pages_skipped,
                "not_visited": coverage.pages_not_visited,
            },
            "critical_issues": critical_issues,
            "recommendations": recommendations,
            "total_duration_seconds": coverage.total_duration_seconds,
        }

    def generate_detailed_report(self) -> CoverageReport:
        """Generate detailed coverage report."""
        coverage = self.tracker.get_extraction_coverage()
        failure_analysis = self.tracker.get_failure_analysis()
        
        # Get lists of pages by status
        covered_pages = self.tracker.get_successful_pages()
        failed_pages = self.tracker.get_failed_pages()
        partial_pages = [p.page_url for p in coverage.pages if p.status == PageStatus.PARTIAL]
        
        # Create statistics
        stats = self._create_coverage_statistics(coverage)
        
        # Generate key findings and recommendations
        critical_issues = self._identify_critical_issues(coverage, failure_analysis)
        recommendations = self._generate_recommendations(coverage, failure_analysis, critical_issues)
        
        # Create summary text
        summary = self._create_summary_text(coverage, stats)
        
        # Create report
        report_id = f"cov_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report = CoverageReport(
            report_id=report_id,
            extraction_id=coverage.extraction_id,
            website_url=coverage.website_url,
            title=f"Coverage Report for {coverage.website_url}",
            summary=summary,
            overall_coverage=stats,
            covered_pages=covered_pages,
            uncovered_pages=[],  # Would need complete page list to determine
            failed_pages=failed_pages,
            critical_issues=critical_issues,
            recommendations=recommendations,
            generated_at=datetime.now().isoformat(),
            notes=self._generate_notes(coverage, failure_analysis),
            next_steps=self._generate_next_steps(coverage),
        )
        
        logger.info(f"Generated detailed coverage report: {report_id}")
        return report

    def generate_page_statistics_report(self) -> Dict[str, Any]:
        """Generate page-by-page statistics."""
        coverage = self.tracker.get_extraction_coverage()
        
        page_stats = {}
        for page in coverage.pages:
            page_stats[page.page_url] = {
                "status": page.status.value if hasattr(page.status, 'value') else str(page.status),
                "components_extracted": page.components_extracted,
                "components_failed": page.components_failed,
                "text_length": page.text_length_chars,
                "duration_seconds": page.extraction_duration_seconds,
                "http_status": page.http_status_code,
                "screenshot_taken": page.screenshot_taken,
                "retry_count": page.retry_count,
                "failure_reason": page.failure_reason.value if page.failure_reason and hasattr(page.failure_reason, 'value') else page.failure_reason,
            }
        
        return {
            "extraction_id": coverage.extraction_id,
            "total_pages": len(page_stats),
            "pages": page_stats,
        }

    def generate_failure_analysis_report(self) -> Dict[str, Any]:
        """Generate detailed failure analysis."""
        failure_analysis = self.tracker.get_failure_analysis()
        failures_by_reason = self.tracker.get_extraction_coverage().failures_by_reason
        
        return {
            "extraction_id": self.tracker.extraction_id,
            "total_failures": failure_analysis["total_failures"],
            "recovered": failure_analysis["recovered"],
            "unrecovered": failure_analysis["unrecovered"],
            "recovery_rate_percentage": failure_analysis["recovery_rate_percentage"],
            "failures_by_reason": failures_by_reason,
            "top_failure_reasons": failure_analysis["top_failure_reasons"],
            "pages_with_most_failures": failure_analysis["pages_with_most_failures"],
        }

    def generate_retry_statistics_report(self) -> Dict[str, Any]:
        """Generate retry attempt statistics."""
        coverage = self.tracker.get_extraction_coverage()
        
        successful_retries = len([r for r in self.tracker.retries if r.succeeded])
        failed_retries = len(self.tracker.retries) - successful_retries
        
        avg_duration = (
            sum(r.duration_seconds for r in self.tracker.retries) / len(self.tracker.retries)
            if self.tracker.retries
            else 0
        )
        
        return {
            "extraction_id": self.tracker.extraction_id,
            "total_retry_attempts": len(self.tracker.retries),
            "successful_retries": successful_retries,
            "failed_retries": failed_retries,
            "success_rate_percentage": (
                (successful_retries / len(self.tracker.retries) * 100)
                if self.tracker.retries
                else 0
            ),
            "average_retry_duration_seconds": avg_duration,
            "retry_reasons": self._get_retry_reasons_distribution(),
        }

    def generate_authentication_report(self) -> Dict[str, Any]:
        """Generate authentication statistics."""
        coverage = self.tracker.get_extraction_coverage()
        total_auth_attempts = coverage.successful_logins + coverage.authentication_failures
        
        return {
            "extraction_id": self.tracker.extraction_id,
            "successful_logins": coverage.successful_logins,
            "authentication_failures": coverage.authentication_failures,
            "total_authentication_attempts": total_auth_attempts,
            "success_rate_percentage": (
                (coverage.successful_logins / total_auth_attempts * 100)
                if total_auth_attempts > 0
                else 0
            ),
        }

    def generate_timing_report(self) -> Dict[str, Any]:
        """Generate timing and performance statistics."""
        coverage = self.tracker.get_extraction_coverage()
        
        # Calculate page statistics
        page_durations = [p.extraction_duration_seconds for p in coverage.pages if p.extraction_duration_seconds > 0]
        
        avg_duration = sum(page_durations) / len(page_durations) if page_durations else 0
        min_duration = min(page_durations) if page_durations else 0
        max_duration = max(page_durations) if page_durations else 0
        
        # Calculate extraction speed
        pages_per_minute = (
            (len(coverage.pages) / coverage.total_duration_seconds * 60)
            if coverage.total_duration_seconds > 0
            else 0
        )
        
        return {
            "extraction_id": self.tracker.extraction_id,
            "start_time": coverage.started_at,
            "end_time": coverage.completed_at,
            "total_duration_seconds": coverage.total_duration_seconds,
            "total_duration_formatted": self._format_duration(coverage.total_duration_seconds),
            "pages_extracted": len(coverage.pages),
            "average_page_duration_seconds": avg_duration,
            "min_page_duration_seconds": min_duration,
            "max_page_duration_seconds": max_duration,
            "extraction_speed_pages_per_minute": pages_per_minute,
            "characters_per_second": (
                coverage.total_text_extracted_chars / coverage.total_duration_seconds
                if coverage.total_duration_seconds > 0
                else 0
            ),
        }

    # Helper methods

    def _create_coverage_statistics(self, coverage) -> CoverageStatistics:
        """Create CoverageStatistics from coverage data."""
        components_by_type = defaultdict(int)
        for page in coverage.pages:
            # This would need actual component type data
            components_by_type["unknown"] += page.components_extracted
        
        pages_by_status = {
            "success": coverage.pages_successful,
            "failed": coverage.pages_failed,
            "partial": coverage.pages_partial,
            "skipped": coverage.pages_skipped,
            "not_visited": coverage.pages_not_visited,
        }
        
        total_auth_attempts = coverage.successful_logins + coverage.authentication_failures
        auth_success_rate = (
            (coverage.successful_logins / total_auth_attempts * 100)
            if total_auth_attempts > 0
            else 0
        )
        
        failure_rate = (
            (coverage.total_failures / coverage.total_pages_attempted * 100)
            if coverage.total_pages_attempted > 0
            else 0
        )
        
        successful_retries = len([r for r in self.tracker.retries if r.succeeded])
        retry_success_rate = (
            (successful_retries / len(self.tracker.retries) * 100)
            if self.tracker.retries
            else 0
        )
        
        avg_page_duration = (
            sum(p.extraction_duration_seconds for p in coverage.pages) / len(coverage.pages)
            if coverage.pages
            else 0
        )
        
        page_durations = [p.extraction_duration_seconds for p in coverage.pages if p.extraction_duration_seconds > 0]
        
        return CoverageStatistics(
            extraction_id=coverage.extraction_id,
            website_url=coverage.website_url,
            total_pages=coverage.total_pages_attempted,
            covered_pages=coverage.pages_successful,
            uncovered_pages=coverage.pages_not_visited,
            coverage_percentage=coverage.coverage_percentage,
            total_component_types=1,  # Simplified
            total_components=coverage.total_components_extracted,
            components_by_type=dict(components_by_type),
            total_text_chars=coverage.total_text_extracted_chars,
            average_chars_per_page=(
                coverage.total_text_extracted_chars / len(coverage.pages) if coverage.pages else 0
            ),
            total_images=0,  # Would need actual image data
            total_failures=coverage.total_failures,
            failure_rate_percentage=failure_rate,
            top_failure_reasons=[r[0] for r in self.tracker._get_top_failure_reasons()],
            total_retries=coverage.total_retry_attempts,
            successful_retries=successful_retries,
            retry_success_rate_percentage=retry_success_rate,
            authentication_attempts=total_auth_attempts,
            authentication_success_rate_percentage=auth_success_rate,
            total_duration_seconds=coverage.total_duration_seconds,
            average_page_duration_seconds=avg_page_duration,
            fastest_page_seconds=min(page_durations) if page_durations else 0,
            slowest_page_seconds=max(page_durations) if page_durations else 0,
            pages_by_status=pages_by_status,
        )

    def _identify_critical_issues(
        self, coverage, failure_analysis
    ) -> List[str]:
        """Identify critical issues from coverage data."""
        issues = []
        
        if coverage.pages_failed > 0:
            issues.append(
                f"High failure rate: {coverage.pages_failed} pages failed "
                f"({coverage.pages_failed / coverage.total_pages_attempted * 100:.1f}%)"
            )
        
        if failure_analysis["recovery_rate_percentage"] < 50 and failure_analysis["total_failures"] > 0:
            issues.append(
                f"Low recovery rate: only {failure_analysis['recovery_rate_percentage']:.1f}% of failures recovered"
            )
        
        if coverage.coverage_percentage < 80:
            issues.append(
                f"Coverage below 80%: achieved {coverage.coverage_percentage:.1f}%"
            )
        
        if coverage.authentication_failures > 0:
            issues.append(
                f"Authentication issues: {coverage.authentication_failures} failures"
            )
        
        return issues

    def _generate_recommendations(
        self, coverage, failure_analysis, critical_issues: List[str]
    ) -> List[str]:
        """Generate recommendations based on coverage data."""
        recommendations = []
        
        if coverage.pages_failed > 0:
            recommendations.append("Review and fix failed page extractions")
            recommendations.append("Analyze failure patterns and implement mitigation strategies")
        
        if len(failure_analysis["top_failure_reasons"]) > 0:
            top_reason = failure_analysis["top_failure_reasons"][0][0]
            recommendations.append(f"Address most common failure: {top_reason}")
        
        if coverage.pages_not_visited > 0:
            recommendations.append("Ensure all pages are discoverable and accessible")
        
        if coverage.total_retry_attempts < 5 and coverage.pages_failed > 0:
            recommendations.append("Implement more aggressive retry strategies for failed pages")
        
        if coverage.coverage_percentage < 80:
            recommendations.append("Expand page discovery to improve coverage")
        
        return recommendations

    def _generate_notes(self, coverage, failure_analysis) -> str:
        """Generate detailed notes about extraction."""
        notes = []
        
        notes.append(f"Extraction ID: {coverage.extraction_id}")
        notes.append(f"Website: {coverage.website_url}")
        notes.append(
            f"Coverage: {coverage.total_pages_attempted} pages attempted, "
            f"{coverage.pages_successful} successful, "
            f"{coverage.pages_failed} failed"
        )
        notes.append(
            f"Content: {coverage.total_text_extracted_chars:,} characters extracted"
        )
        notes.append(
            f"Components: {coverage.total_components_extracted} components extracted"
        )
        notes.append(
            f"Recovery: {failure_analysis['recovered']} of {failure_analysis['total_failures']} "
            f"failures recovered ({failure_analysis['recovery_rate_percentage']:.1f}%)"
        )
        
        return "\n".join(notes)

    def _generate_next_steps(self, coverage) -> str:
        """Generate next steps for improvement."""
        steps = []
        
        if coverage.pages_failed > 0:
            steps.append("1. Investigate failed page extractions")
        
        if coverage.pages_not_visited > 0:
            steps.append(f"2. Improve page discovery to cover remaining {coverage.pages_not_visited} pages")
        
        if coverage.total_retry_attempts < 5:
            steps.append("3. Implement retry mechanisms for failed extractions")
        
        steps.append("4. Review and optimize extraction performance")
        steps.append("5. Run compliance comparison on extracted data")
        
        return "\n".join(steps)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    def _get_retry_reasons_distribution(self) -> Dict[str, int]:
        """Get distribution of retry reasons."""
        reasons = defaultdict(int)
        for retry in self.tracker.retries:
            reasons[retry.reason_for_retry] += 1
        return dict(sorted(reasons.items(), key=lambda x: x[1], reverse=True))
