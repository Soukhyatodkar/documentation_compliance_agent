"""
Coverage data storage and retrieval.

Handles persistent storage of coverage tracking data
and provides query interfaces for analysis.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.coverage.models import (
    ExtractionCoverage,
    FailureLog,
    RetryAttempt,
    CoverageStatistics,
    CoverageReport,
    ExtractionCheckpoint,
    ExtractionProgress,
    PageCoverage,
)
from src.core.exceptions import StorageError


logger = logging.getLogger(__name__)


class CoverageStorage:
    """Base storage class for coverage data."""

    def __init__(self, base_path: str):
        """Initialize coverage storage."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.coverage_dir = self.base_path / "coverage"
        self.coverage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized coverage storage at {self.coverage_dir}")

    def _ensure_directory(self, directory: str) -> Path:
        """Ensure directory exists."""
        dir_path = self.coverage_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path


class ExtractionCoverageStorage(CoverageStorage):
    """Storage for extraction coverage data."""

    DIRECTORY = "extractions"

    def __init__(self, base_path: str):
        """Initialize extraction coverage storage."""
        super().__init__(base_path)
        self.coverage_subdir = self._ensure_directory(self.DIRECTORY)

    def save_coverage(self, coverage: ExtractionCoverage) -> str:
        """Save extraction coverage to file."""
        try:
            filename = f"{coverage.extraction_id}_coverage.json"
            filepath = self.coverage_subdir / filename

            data = coverage.dict()
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved coverage for extraction {coverage.extraction_id}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save coverage: {e}")
            raise StorageError(f"Failed to save coverage: {e}")

    def load_coverage(self, extraction_id: str) -> Optional[ExtractionCoverage]:
        """Load extraction coverage from file."""
        try:
            filename = f"{extraction_id}_coverage.json"
            filepath = self.coverage_subdir / filename

            if not filepath.exists():
                logger.warning(f"Coverage file not found: {filepath}")
                return None

            with open(filepath, "r") as f:
                data = json.load(f)

            coverage = ExtractionCoverage(**data)
            logger.info(f"Loaded coverage for extraction {extraction_id}")
            return coverage
        except Exception as e:
            logger.error(f"Failed to load coverage for {extraction_id}: {e}")
            raise StorageError(f"Failed to load coverage: {e}")

    def list_extractions(self) -> List[str]:
        """List all extraction IDs."""
        extraction_ids = []
        for filepath in self.coverage_subdir.glob("*_coverage.json"):
            extraction_id = filepath.name.replace("_coverage.json", "")
            extraction_ids.append(extraction_id)
        return sorted(extraction_ids)


class FailureLogStorage(CoverageStorage):
    """Storage for failure logs."""

    DIRECTORY = "failures"

    def __init__(self, base_path: str):
        """Initialize failure log storage."""
        super().__init__(base_path)
        self.failures_subdir = self._ensure_directory(self.DIRECTORY)

    def save_failures(self, failures: List[FailureLog], extraction_id: str) -> str:
        """Save failure logs to file."""
        try:
            filename = f"{extraction_id}_failures.json"
            filepath = self.failures_subdir / filename

            data = [f.dict() for f in failures]
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved {len(failures)} failure logs for extraction {extraction_id}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save failure logs: {e}")
            raise StorageError(f"Failed to save failure logs: {e}")

    def load_failures(self, extraction_id: str) -> List[FailureLog]:
        """Load failure logs from file."""
        try:
            filename = f"{extraction_id}_failures.json"
            filepath = self.failures_subdir / filename

            if not filepath.exists():
                logger.warning(f"Failure log file not found: {filepath}")
                return []

            with open(filepath, "r") as f:
                data = json.load(f)

            failures = [FailureLog(**item) for item in data]
            logger.info(f"Loaded {len(failures)} failure logs for extraction {extraction_id}")
            return failures
        except Exception as e:
            logger.error(f"Failed to load failure logs: {e}")
            raise StorageError(f"Failed to load failure logs: {e}")


class RetryStorage(CoverageStorage):
    """Storage for retry attempt logs."""

    DIRECTORY = "retries"

    def __init__(self, base_path: str):
        """Initialize retry storage."""
        super().__init__(base_path)
        self.retries_subdir = self._ensure_directory(self.DIRECTORY)

    def save_retries(self, retries: List[RetryAttempt], extraction_id: str) -> str:
        """Save retry logs to file."""
        try:
            filename = f"{extraction_id}_retries.json"
            filepath = self.retries_subdir / filename

            data = [r.dict() for r in retries]
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved {len(retries)} retry logs for extraction {extraction_id}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save retry logs: {e}")
            raise StorageError(f"Failed to save retry logs: {e}")

    def load_retries(self, extraction_id: str) -> List[RetryAttempt]:
        """Load retry logs from file."""
        try:
            filename = f"{extraction_id}_retries.json"
            filepath = self.retries_subdir / filename

            if not filepath.exists():
                logger.warning(f"Retry log file not found: {filepath}")
                return []

            with open(filepath, "r") as f:
                data = json.load(f)

            retries = [RetryAttempt(**item) for item in data]
            logger.info(f"Loaded {len(retries)} retry logs for extraction {extraction_id}")
            return retries
        except Exception as e:
            logger.error(f"Failed to load retry logs: {e}")
            raise StorageError(f"Failed to load retry logs: {e}")


class CheckpointStorage(CoverageStorage):
    """Storage for extraction checkpoints."""

    DIRECTORY = "checkpoints"

    def __init__(self, base_path: str):
        """Initialize checkpoint storage."""
        super().__init__(base_path)
        self.checkpoints_subdir = self._ensure_directory(self.DIRECTORY)

    def save_checkpoint(self, checkpoint: ExtractionCheckpoint, extraction_id: str) -> str:
        """Save individual checkpoint."""
        try:
            filename = f"{extraction_id}_checkpoint_{checkpoint.checkpoint_number}.json"
            filepath = self.checkpoints_subdir / filename

            data = checkpoint.dict()
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved checkpoint {checkpoint.checkpoint_number} for {extraction_id}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise StorageError(f"Failed to save checkpoint: {e}")

    def load_checkpoints(self, extraction_id: str) -> List[ExtractionCheckpoint]:
        """Load all checkpoints for extraction."""
        try:
            checkpoints = []
            for filepath in self.checkpoints_subdir.glob(f"{extraction_id}_checkpoint_*.json"):
                with open(filepath, "r") as f:
                    data = json.load(f)
                checkpoints.append(ExtractionCheckpoint(**data))
            
            checkpoints.sort(key=lambda c: c.checkpoint_number)
            logger.info(f"Loaded {len(checkpoints)} checkpoints for {extraction_id}")
            return checkpoints
        except Exception as e:
            logger.error(f"Failed to load checkpoints: {e}")
            raise StorageError(f"Failed to load checkpoints: {e}")


class CoverageReportStorage(CoverageStorage):
    """Storage for coverage reports."""

    DIRECTORY = "reports"

    def __init__(self, base_path: str):
        """Initialize report storage."""
        super().__init__(base_path)
        self.reports_subdir = self._ensure_directory(self.DIRECTORY)

    def save_report(self, report: CoverageReport) -> str:
        """Save coverage report to file."""
        try:
            filename = f"{report.report_id}_report.json"
            filepath = self.reports_subdir / filename

            data = report.dict()
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved coverage report {report.report_id}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save coverage report: {e}")
            raise StorageError(f"Failed to save coverage report: {e}")

    def load_report(self, report_id: str) -> Optional[CoverageReport]:
        """Load coverage report from file."""
        try:
            filename = f"{report_id}_report.json"
            filepath = self.reports_subdir / filename

            if not filepath.exists():
                logger.warning(f"Report file not found: {filepath}")
                return None

            with open(filepath, "r") as f:
                data = json.load(f)

            report = CoverageReport(**data)
            logger.info(f"Loaded coverage report {report_id}")
            return report
        except Exception as e:
            logger.error(f"Failed to load coverage report: {e}")
            raise StorageError(f"Failed to load coverage report: {e}")

    def list_reports(self) -> List[str]:
        """List all report IDs."""
        report_ids = []
        for filepath in self.reports_subdir.glob("*_report.json"):
            report_id = filepath.name.replace("_report.json", "")
            report_ids.append(report_id)
        return sorted(report_ids)


class CoverageQuery:
    """Query interface for coverage data."""

    def __init__(
        self,
        coverage_storage: ExtractionCoverageStorage,
        failure_storage: FailureLogStorage,
        retry_storage: RetryStorage,
    ):
        """Initialize query interface."""
        self.coverage_storage = coverage_storage
        self.failure_storage = failure_storage
        self.retry_storage = retry_storage
        logger.info("Initialized coverage query interface")

    def get_extraction_summary(self, extraction_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of extraction coverage."""
        coverage = self.coverage_storage.load_coverage(extraction_id)
        if not coverage:
            return None

        return {
            "extraction_id": coverage.extraction_id,
            "website_url": coverage.website_url,
            "total_pages_attempted": coverage.total_pages_attempted,
            "pages_successful": coverage.pages_successful,
            "pages_failed": coverage.pages_failed,
            "pages_partial": coverage.pages_partial,
            "pages_skipped": coverage.pages_skipped,
            "pages_not_visited": coverage.pages_not_visited,
            "coverage_percentage": coverage.coverage_percentage,
            "success_percentage": coverage.success_percentage,
            "components_extracted": coverage.total_components_extracted,
            "text_chars_extracted": coverage.total_text_extracted_chars,
            "total_failures": coverage.total_failures,
            "total_retries": coverage.total_retry_attempts,
            "authentication_failures": coverage.authentication_failures,
            "successful_logins": coverage.successful_logins,
            "total_duration_seconds": coverage.total_duration_seconds,
        }

    def get_critical_failures(self, extraction_id: str) -> List[Dict[str, Any]]:
        """Get failures that were not recovered."""
        failures = self.failure_storage.load_failures(extraction_id)
        critical = [f for f in failures if not f.recovered]
        return [f.dict() for f in critical]

    def get_most_failed_pages(self, extraction_id: str, limit: int = 5) -> List[tuple]:
        """Get pages with most failures."""
        failures = self.failure_storage.load_failures(extraction_id)
        page_failure_count = {}
        for failure in failures:
            page_failure_count[failure.page_url] = page_failure_count.get(failure.page_url, 0) + 1
        
        sorted_pages = sorted(page_failure_count.items(), key=lambda x: x[1], reverse=True)
        return sorted_pages[:limit]

    def get_retry_effectiveness(self, extraction_id: str) -> Dict[str, Any]:
        """Get retry attempt effectiveness."""
        retries = self.retry_storage.load_retries(extraction_id)
        successful = len([r for r in retries if r.succeeded])
        failed = len(retries) - successful
        
        return {
            "total_retries": len(retries),
            "successful_retries": successful,
            "failed_retries": failed,
            "success_rate_percentage": (
                (successful / len(retries) * 100) if retries else 0
            ),
            "average_retry_duration_seconds": (
                sum(r.duration_seconds for r in retries) / len(retries) if retries else 0
            ),
        }

    def get_failure_reasons_distribution(self, extraction_id: str) -> Dict[str, int]:
        """Get distribution of failures by reason."""
        failures = self.failure_storage.load_failures(extraction_id)
        distribution = {}
        for failure in failures:
            reason_key = failure.reason.value if hasattr(failure.reason, 'value') else str(failure.reason)
            distribution[reason_key] = distribution.get(reason_key, 0) + 1
        
        return dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))

    def get_progress_over_time(self, extraction_id: str, checkpoint_storage: CheckpointStorage) -> List[Dict[str, Any]]:
        """Get extraction progress over time using checkpoints."""
        checkpoints = checkpoint_storage.load_checkpoints(extraction_id)
        progress_data = []
        
        for checkpoint in checkpoints:
            progress_data.append({
                "checkpoint_number": checkpoint.checkpoint_number,
                "timestamp": checkpoint.created_at,
                "progress_percentage": checkpoint.progress_percentage,
                "pages_processed": checkpoint.pages_processed,
                "components_extracted": checkpoint.components_extracted,
                "failures": checkpoint.failures_so_far,
                "estimated_completion": checkpoint.estimated_completion_time,
            })
        
        return progress_data
