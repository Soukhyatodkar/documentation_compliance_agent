"""
Data storage and retrieval module.

Handles persistent storage of canonical data structures
in JSON files and provides querying capabilities.
"""

import json
import os
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import logging
from src.core.exceptions import StorageError, ValidationError

from src.data.models import (
    WebComponent,
    WebPage,
    WebsiteExtraction,
    GuidelineChunk,
    Discrepancy,
    DiscrepancyReport,
    ComparisonResult,
)
from src.data.schema import (
    SchemaConverter,
    SchemaNormalizer,
    SchemaExporter,
    SchemaValidator,
)
from src.core.exceptions import StorageError, ValidationError
from src.utils.helpers import PathHelper


logger = logging.getLogger(__name__)


class DataStorage:
    """Base class for data storage operations."""

    def __init__(self, base_path: str):
        """Initialize storage with base directory."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized data storage at {self.base_path}")

    def _get_file_path(self, filename: str) -> Path:
        """Get full file path."""
        return self.base_path / filename

    def _ensure_directory(self, directory: str) -> Path:
        """Ensure directory exists."""
        dir_path = self.base_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path


class WebExtractionStorage(DataStorage):
    """Storage for website extraction data."""

    DIRECTORY = "extractions"

    def __init__(self, base_path: str):
        """Initialize extraction storage."""
        super().__init__(base_path)
        self.extractions_dir = self._ensure_directory(self.DIRECTORY)

    def save_extraction(self, extraction: WebsiteExtraction) -> str:
        """Save extraction to file."""
        try:
            filename = f"{extraction.extraction_id}.json"
            filepath = self.extractions_dir / filename

            # Convert to JSON
            data = SchemaConverter.extraction_to_dict(extraction)

            # Write to file
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved extraction {extraction.extraction_id} to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save extraction: {e}")
            raise StorageError(f"Failed to save extraction: {e}")

    def load_extraction(self, extraction_id: str) -> Optional[WebsiteExtraction]:
        """Load extraction from file."""
        try:
            filename = f"{extraction_id}.json"
            filepath = self.extractions_dir / filename

            if not filepath.exists():
                logger.warning(f"Extraction file not found: {filepath}")
                return None

            with open(filepath, "r") as f:
                data = json.load(f)

            extraction = SchemaConverter.extraction_from_dict(data)
            logger.info(f"Loaded extraction {extraction_id}")
            return extraction
        except Exception as e:
            logger.error(f"Failed to load extraction {extraction_id}: {e}")
            raise StorageError(f"Failed to load extraction: {e}")

    def list_extractions(self) -> List[str]:
        """List all extraction IDs."""
        extraction_ids = []
        for filepath in self.extractions_dir.glob("*.json"):
            extraction_ids.append(filepath.stem)
        return sorted(extraction_ids)

    def delete_extraction(self, extraction_id: str) -> bool:
        """Delete extraction file."""
        try:
            filename = f"{extraction_id}.json"
            filepath = self.extractions_dir / filename

            if filepath.exists():
                filepath.unlink()
                logger.info(f"Deleted extraction {extraction_id}")
                return True
            else:
                logger.warning(f"Extraction file not found: {filepath}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete extraction: {e}")
            raise StorageError(f"Failed to delete extraction: {e}")

    def count_extractions(self) -> int:
        """Count total extractions."""
        return len(list(self.extractions_dir.glob("*.json")))


class GuidelineChunkStorage(DataStorage):
    """Storage for guideline chunks."""

    DIRECTORY = "guidelines"

    def __init__(self, base_path: str):
        """Initialize guideline storage."""
        super().__init__(base_path)
        self.guidelines_dir = self._ensure_directory(self.DIRECTORY)

    def save_chunks(self, chunks: List[GuidelineChunk], source_name: str) -> str:
        """Save guideline chunks to file."""
        try:
            filename = f"{source_name}_chunks.json"
            filepath = self.guidelines_dir / filename

            # Convert chunks to dictionaries
            data = [chunk.dict() for chunk in chunks]

            # Write to file
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved {len(chunks)} chunks to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save chunks: {e}")
            raise StorageError(f"Failed to save chunks: {e}")

    def load_chunks(self, source_name: str) -> List[GuidelineChunk]:
        """Load guideline chunks from file."""
        try:
            filename = f"{source_name}_chunks.json"
            filepath = self.guidelines_dir / filename

            if not filepath.exists():
                logger.warning(f"Chunks file not found: {filepath}")
                return []

            with open(filepath, "r") as f:
                data = json.load(f)

            chunks = [GuidelineChunk(**item) for item in data]
            logger.info(f"Loaded {len(chunks)} chunks from {source_name}")
            return chunks
        except Exception as e:
            logger.error(f"Failed to load chunks from {source_name}: {e}")
            raise StorageError(f"Failed to load chunks: {e}")

    def list_sources(self) -> List[str]:
        """List all guideline sources."""
        sources = []
        for filepath in self.guidelines_dir.glob("*_chunks.json"):
            # Remove "_chunks.json" suffix
            source_name = filepath.name.replace("_chunks.json", "")
            sources.append(source_name)
        return sorted(sources)


class DiscrepancyStorage(DataStorage):
    """Storage for discrepancy data."""

    DIRECTORY = "discrepancies"

    def __init__(self, base_path: str):
        """Initialize discrepancy storage."""
        super().__init__(base_path)
        self.discrepancies_dir = self._ensure_directory(self.DIRECTORY)

    def save_report(self, report: DiscrepancyReport) -> str:
        """Save discrepancy report to file."""
        try:
            filename = f"{report.report_id}_report.json"
            filepath = self.discrepancies_dir / filename

            # Convert to JSON
            data = SchemaConverter.report_to_dict(report)

            # Write to file
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved report {report.report_id} to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            raise StorageError(f"Failed to save report: {e}")

    def load_report(self, report_id: str) -> Optional[DiscrepancyReport]:
        """Load discrepancy report from file."""
        try:
            filename = f"{report_id}_report.json"
            filepath = self.discrepancies_dir / filename

            if not filepath.exists():
                logger.warning(f"Report file not found: {filepath}")
                return None

            with open(filepath, "r") as f:
                data = json.load(f)

            report = SchemaConverter.report_from_dict(data)
            logger.info(f"Loaded report {report_id}")
            return report
        except Exception as e:
            logger.error(f"Failed to load report {report_id}: {e}")
            raise StorageError(f"Failed to load report: {e}")

    def save_discrepancies(
        self, discrepancies: List[Discrepancy], extraction_id: str
    ) -> str:
        """Save discrepancies to file."""
        try:
            filename = f"{extraction_id}_discrepancies.json"
            filepath = self.discrepancies_dir / filename

            # Convert to dictionaries
            data = [disc.dict() for disc in discrepancies]

            # Write to file
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved {len(discrepancies)} discrepancies to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save discrepancies: {e}")
            raise StorageError(f"Failed to save discrepancies: {e}")

    def load_discrepancies(self, extraction_id: str) -> List[Discrepancy]:
        """Load discrepancies from file."""
        try:
            filename = f"{extraction_id}_discrepancies.json"
            filepath = self.discrepancies_dir / filename

            if not filepath.exists():
                logger.warning(f"Discrepancies file not found: {filepath}")
                return []

            with open(filepath, "r") as f:
                data = json.load(f)

            discrepancies = [Discrepancy(**item) for item in data]
            logger.info(f"Loaded {len(discrepancies)} discrepancies from {extraction_id}")
            return discrepancies
        except Exception as e:
            logger.error(f"Failed to load discrepancies from {extraction_id}: {e}")
            raise StorageError(f"Failed to load discrepancies: {e}")

    def list_reports(self) -> List[str]:
        """List all report IDs."""
        report_ids = []
        for filepath in self.discrepancies_dir.glob("*_report.json"):
            # Remove "_report.json" suffix
            report_id = filepath.name.replace("_report.json", "")
            report_ids.append(report_id)
        return sorted(report_ids)

    def count_discrepancies(self, extraction_id: str) -> int:
        """Count discrepancies for extraction."""
        filename = f"{extraction_id}_discrepancies.json"
        filepath = self.discrepancies_dir / filename

        if not filepath.exists():
            return 0

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            return len(data)
        except Exception:
            return 0


class ComparisonResultStorage(DataStorage):
    """Storage for comparison results."""

    DIRECTORY = "comparisons"

    def __init__(self, base_path: str):
        """Initialize comparison storage."""
        super().__init__(base_path)
        self.comparisons_dir = self._ensure_directory(self.DIRECTORY)

    def save_results(
        self, results: List[ComparisonResult], extraction_id: str, batch_id: int = 0
    ) -> str:
        """Save comparison results to file."""
        try:
            filename = f"{extraction_id}_comparison_batch_{batch_id}.json"
            filepath = self.comparisons_dir / filename

            # Convert to dictionaries
            data = [result.dict() for result in results]

            # Write to file
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved {len(results)} comparison results to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save comparison results: {e}")
            raise StorageError(f"Failed to save comparison results: {e}")

    def load_results(self, extraction_id: str, batch_id: int = 0) -> List[ComparisonResult]:
        """Load comparison results from file."""
        try:
            filename = f"{extraction_id}_comparison_batch_{batch_id}.json"
            filepath = self.comparisons_dir / filename

            if not filepath.exists():
                logger.warning(f"Comparison results file not found: {filepath}")
                return []

            with open(filepath, "r") as f:
                data = json.load(f)

            results = [ComparisonResult(**item) for item in data]
            logger.info(f"Loaded {len(results)} comparison results from batch {batch_id}")
            return results
        except Exception as e:
            logger.error(f"Failed to load comparison results: {e}")
            raise StorageError(f"Failed to load comparison results: {e}")


class DataQuery:
    """Query interface for stored data."""

    def __init__(
        self,
        extraction_storage: WebExtractionStorage,
        discrepancy_storage: DiscrepancyStorage,
    ):
        """Initialize query interface."""
        self.extraction_storage = extraction_storage
        self.discrepancy_storage = discrepancy_storage
        logger.info("Initialized data query interface")

    def get_extraction_summary(self, extraction_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of extraction."""
        extraction = self.extraction_storage.load_extraction(extraction_id)
        if not extraction:
            return None

        return {
            "extraction_id": extraction.extraction_id,
            "website_url": extraction.website_url,
            "total_pages_extracted": extraction.total_pages_extracted,
            "total_pages_attempted": extraction.total_pages_attempted,
            "total_components": sum(
                len(page.components) for page in extraction.pages
            ),
            "started_at": extraction.started_at,
            "completed_at": extraction.completed_at,
            "errors_count": len(extraction.extraction_errors),
        }

    def get_discrepancies_by_severity(
        self, extraction_id: str
    ) -> Dict[str, List[Discrepancy]]:
        """Get discrepancies grouped by severity."""
        discrepancies = self.discrepancy_storage.load_discrepancies(extraction_id)

        grouped = {
            "critical": [],
            "warning": [],
            "info": [],
            "note": [],
        }
        for disc in discrepancies:
            severity_key = disc.severity.value
            if severity_key in grouped:
                grouped[severity_key].append(disc)

        return grouped

    def get_discrepancies_by_page(self, extraction_id: str) -> Dict[str, List[Discrepancy]]:
        """Get discrepancies grouped by page."""
        discrepancies = self.discrepancy_storage.load_discrepancies(extraction_id)

        grouped = {}
        for disc in discrepancies:
            page_url = disc.page_url
            if page_url not in grouped:
                grouped[page_url] = []
            grouped[page_url].append(disc)

        return grouped

    def get_discrepancies_by_component_type(
        self, extraction_id: str
    ) -> Dict[str, List[Discrepancy]]:
        """Get discrepancies grouped by component type."""
        discrepancies = self.discrepancy_storage.load_discrepancies(extraction_id)

        grouped = {}
        for disc in discrepancies:
            comp_type = disc.component_type.value
            if comp_type not in grouped:
                grouped[comp_type] = []
            grouped[comp_type].append(disc)

        return grouped

    def filter_discrepancies(
        self,
        extraction_id: str,
        predicate: Callable[[Discrepancy], bool],
    ) -> List[Discrepancy]:
        """Filter discrepancies using predicate function."""
        discrepancies = self.discrepancy_storage.load_discrepancies(extraction_id)
        return [disc for disc in discrepancies if predicate(disc)]

    def get_high_confidence_issues(
        self, extraction_id: str, min_confidence: float = 0.8
    ) -> List[Discrepancy]:
        """Get high-confidence discrepancies."""
        return self.filter_discrepancies(
            extraction_id, lambda d: d.confidence_score >= min_confidence
        )

    def get_critical_issues(self, extraction_id: str) -> List[Discrepancy]:
        """Get all critical severity discrepancies."""
        from src.data.models import SeverityLevel

        return self.filter_discrepancies(
            extraction_id,
            lambda d: d.severity == SeverityLevel.CRITICAL,
        )


class BatchDataProcessor:
    """Process data in batches for efficiency."""

    def __init__(
        self,
        extraction_storage: WebExtractionStorage,
        chunk_size: int = 100,
    ):
        """Initialize batch processor."""
        self.extraction_storage = extraction_storage
        self.chunk_size = chunk_size
        logger.info(f"Initialized batch processor with chunk size {chunk_size}")

    def process_pages_batch(
        self,
        extraction_id: str,
        process_func: Callable[[WebPage], Any],
    ) -> List[Any]:
        """Process pages in extraction in batches."""
        extraction = self.extraction_storage.load_extraction(extraction_id)
        if not extraction:
            logger.warning(f"Extraction {extraction_id} not found")
            return []

        results = []
        for i, page in enumerate(extraction.pages):
            try:
                result = process_func(page)
                results.append(result)
                if (i + 1) % self.chunk_size == 0:
                    logger.info(f"Processed {i + 1} pages")
            except Exception as e:
                logger.error(f"Error processing page {page.page_id}: {e}")

        logger.info(f"Completed processing {len(extraction.pages)} pages")
        return results

    def process_discrepancies_batch(
        self,
        extraction_id: str,
        discrepancy_storage: DiscrepancyStorage,
        process_func: Callable[[Discrepancy], Any],
    ) -> List[Any]:
        """Process discrepancies in batches."""
        discrepancies = discrepancy_storage.load_discrepancies(extraction_id)

        results = []
        for i, discrepancy in enumerate(discrepancies):
            try:
                result = process_func(discrepancy)
                results.append(result)
                if (i + 1) % self.chunk_size == 0:
                    logger.info(f"Processed {i + 1} discrepancies")
            except Exception as e:
                logger.error(f"Error processing discrepancy {discrepancy.discrepancy_id}: {e}")

        logger.info(f"Completed processing {len(discrepancies)} discrepancies")
        return results


# Alias for backward compatibility with CLI
class DataStore:
    """
    Main data store interface for CLI and orchestration.
    
    Provides unified access to all storage operations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize DataStore with configuration."""
        if config is None:
            config = {}
        
        # Get base directory from config
        base_dir = config.get("output", {}).get("base_dir", "./data")
        
        # Initialize all storage backends
        self.extraction = WebExtractionStorage(base_dir)
        self.guidelines = GuidelineChunkStorage(base_dir)
        self.discrepancies = DiscrepancyStorage(base_dir)
        self.comparisons = ComparisonResultStorage(base_dir)
        self.query = DataQuery(self.extraction, self.discrepancies)
        self.batch = BatchDataProcessor(self.extraction)
        
        logger.info(f"Initialized DataStore with base directory: {base_dir}")
    
    # Delegation methods for backward compatibility
    def save_component(self, component: WebComponent) -> None:
        """Save a web component (mock implementation)."""
        # In a full implementation, would store the component
        pass
    
    def get_component(self, component_id: str) -> Optional[WebComponent]:
        """Get a web component by ID (mock implementation)."""
        return None
    
    def save_comparison_result(self, result: ComparisonResult) -> None:
        """Save comparison result."""
        try:
            self.comparisons.save_results([result], result.extraction_id)
        except Exception as e:
            logger.error(f"Failed to save comparison result: {e}")
    
    def save_discrepancy(self, discrepancy: Discrepancy) -> None:
        """Save discrepancy."""
        try:
            self.discrepancies.save_discrepancies([discrepancy], discrepancy.page_url)
        except Exception as e:
            logger.error(f"Failed to save discrepancy: {e}")
    
    def get_components(self) -> List[WebComponent]:
        """Get all stored components."""
        return []
    
    def get_comparison_results(self) -> List[ComparisonResult]:
        """Get all comparison results."""
        results = []
        try:
            extraction_ids = self.extraction.list_extractions()
            for ext_id in extraction_ids:
                results.extend(self.comparisons.load_results(ext_id))
        except Exception as e:
            logger.error(f"Failed to get comparison results: {e}")
        return results
    
    def get_discrepancies(self) -> List[Discrepancy]:
        """Get all stored discrepancies."""
        discrepancies = []
        try:
            extraction_ids = self.extraction.list_extractions()
            for ext_id in extraction_ids:
                discrepancies.extend(self.discrepancies.load_discrepancies(ext_id))
        except Exception as e:
            logger.error(f"Failed to get discrepancies: {e}")
        return discrepancies
    
    def count_components(self) -> int:
        """Count total components."""
        return 0  # Mock implementation
    
    def count_comparison_results(self) -> int:
        """Count total comparison results."""
        try:
            count = 0
            extraction_ids = self.extraction.list_extractions()
            for ext_id in extraction_ids:
                count += len(self.comparisons.load_results(ext_id))
            return count
        except Exception:
            return 0
    
    def count_discrepancies(self) -> int:
        """Count total discrepancies."""
        try:
            count = 0
            extraction_ids = self.extraction.list_extractions()
            for ext_id in extraction_ids:
                count += len(self.discrepancies.load_discrepancies(ext_id))
            return count
        except Exception:
            return 0
