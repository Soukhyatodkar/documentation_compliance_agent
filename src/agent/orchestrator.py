"""
Compliance Orchestrator - Coordinates the full compliance checking pipeline.

Manages the flow from web components through RAG retrieval to LLM comparison
and discrepancy detection.

Features:
- End-to-end pipeline orchestration
- Progress tracking
- Error recovery
- Result aggregation
- Report generation hooks
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

import structlog

from src.core.config import get_config
from src.core.exceptions import ValidationError, ProcessingError
from src.core.logger import setup_logging
from src.data.models import (
    WebComponent,
    WebPage,
    ComparisonContext,
    Discrepancy,
    ComparisonResult,
)
from src.rag.retriever import SemanticRetriever
from src.rag.context import ContextBuilder
from src.vector_store.embeddings import EmbeddingGenerator
from src.vector_store.qdrant_client import QdrantVectorStore
from src.agent.compliance_agent import ComplianceAgent, ComparisonAssessment


logger = structlog.get_logger(__name__)


class ComplianceOrchestrator:
    """
    Orchestrates the full compliance checking pipeline.

    Coordinates:
    1. RAG retrieval of relevant guidelines
    2. LLM-based comparison
    3. Discrepancy detection
    4. Result aggregation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize orchestrator.

        Args:
            config: Configuration dictionary. If None, loads from environment.

        Raises:
            ValidationError: If configuration is invalid.
        """
        self._config = config or get_config()

        # Initialize components
        self._embedder = EmbeddingGenerator(self._config)
        self._vector_store = QdrantVectorStore(self._config)
        self._retriever = SemanticRetriever(self._embedder, self._vector_store)
        self._context_builder = ContextBuilder(self._config)
        self._agent = ComplianceAgent(self._config, use_async=True)

        # Tracking
        self._processed_components = 0
        self._detected_discrepancies = 0
        self._processing_errors = 0

        logger.info("Compliance orchestrator initialized")

    async def check_page(
        self,
        page: WebPage,
        page_components: List[WebComponent],
        screenshot_dir: Optional[str] = None,
    ) -> ComparisonResult:
        """
        Check all components on a page for compliance.

        Args:
            page: WebPage object with metadata.
            page_components: List of components extracted from page.
            screenshot_dir: Directory containing component screenshots.

        Returns:
            ComparisonResult with all discrepancies and statistics.

        Raises:
            ProcessingError: If processing fails.
        """
        logger.info(
            "Starting page compliance check",
            page_url=page.page_url,
            component_count=len(page_components),
        )

        discrepancies: List[Discrepancy] = []
        assessments: List[ComparisonAssessment] = []

        try:
            # Process each component
            for component in page_components:
                try:
                    # Retrieve relevant guidelines
                    retrieval_results = self._retriever.retrieve_by_component(
                        component.actual_text or component.selector,
                        component_type=component.component_type.value,
                        context_text=page.page_title,
                    )

                    # Build comparison context
                    context = self._context_builder.build_comparison_context(
                        component=component,
                        retrieval_results=retrieval_results,
                        page_context=page.page_title,
                    )

                    # Compare component
                    assessment = await self._agent.compare_component(
                        component, context
                    )

                    assessments.append(assessment)

                    # Detect discrepancies
                    screenshot_path = (
                        f"{screenshot_dir}/{component.component_id}.png"
                        if screenshot_dir
                        else None
                    )

                    component_discrepancies = (
                        self._agent.detect_discrepancies(
                            component,
                            assessment,
                            page.page_url,
                            screenshot_path,
                        )
                    )

                    discrepancies.extend(component_discrepancies)
                    self._detected_discrepancies += len(component_discrepancies)
                    self._processed_components += 1

                except Exception as e:
                    logger.error(
                        "Component processing failed",
                        component_id=component.component_id,
                        error=str(e),
                    )
                    self._processing_errors += 1
                    continue

        except Exception as e:
            logger.error("Page check failed", page_url=page.page_url, error=str(e))
            raise ProcessingError(f"Page compliance check failed: {e}") from e

        # Aggregate results
        result = self._aggregate_results(
            page, page_components, assessments, discrepancies
        )

        logger.info(
            "Page compliance check complete",
            page_url=page.page_url,
            discrepancy_count=len(discrepancies),
        )

        return result

    async def check_website(
        self,
        pages: List[WebPage],
        components_by_page: Dict[str, List[WebComponent]],
        screenshot_dir: Optional[str] = None,
    ) -> Dict[str, ComparisonResult]:
        """
        Check all pages of a website for compliance.

        Args:
            pages: List of WebPage objects.
            components_by_page: Mapping of page URL to components.
            screenshot_dir: Directory containing screenshots.

        Returns:
            Mapping of page URL to ComparisonResult.

        Raises:
            ValidationError: If inputs are invalid.
        """
        if not pages:
            raise ValidationError("No pages provided")

        logger.info(
            "Starting website compliance check",
            page_count=len(pages),
            total_components=sum(
                len(components) for components in components_by_page.values()
            ),
        )

        results: Dict[str, ComparisonResult] = {}

        # Process pages sequentially (can be made parallel if needed)
        for page in pages:
            page_components = components_by_page.get(page.page_url, [])

            try:
                result = await self.check_page(
                    page, page_components, screenshot_dir
                )
                results[page.page_url] = result
            except Exception as e:
                logger.error(
                    "Page processing failed",
                    page_url=page.page_url,
                    error=str(e),
                )
                continue

        # Aggregate all results
        total_discrepancies = sum(
            len(result.discrepancies) for result in results.values()
        )

        logger.info(
            "Website compliance check complete",
            pages_checked=len(results),
            total_discrepancies=total_discrepancies,
        )

        return results

    async def check_components_batch(
        self,
        components: List[WebComponent],
        page_url: str,
        screenshot_dir: Optional[str] = None,
    ) -> List[Discrepancy]:
        """
        Check multiple components in batch.

        Args:
            components: List of components to check.
            page_url: URL of page containing components.
            screenshot_dir: Directory containing screenshots.

        Returns:
            List of detected discrepancies.
        """
        logger.info(
            "Starting batch component check",
            component_count=len(components),
            page_url=page_url,
        )

        discrepancies: List[Discrepancy] = []

        # Build contexts for all components
        contexts: List[ComparisonContext] = []
        valid_components: List[WebComponent] = []

        for component in components:
            try:
                retrieval_results = (
                    self._retriever.retrieve_by_component(
                        component.actual_text or component.selector,
                        component_type=component.component_type.value,
                        context_text=f"Page: {page_url}",
                    )
                )

                context = self._context_builder.build_comparison_context(
                    component=component,
                    retrieval_results=retrieval_results,
                    page_context=page_url,
                )

                contexts.append(context)
                valid_components.append(component)

            except Exception as e:
                logger.warning(
                    "Failed to build context for component",
                    component_id=component.component_id,
                    error=str(e),
                )
                self._processing_errors += 1
                continue

        # Run comparisons concurrently
        if valid_components:
            assessments = await self._agent.compare_components_batch(
                valid_components, contexts, max_concurrent=5
            )

            # Convert assessments to discrepancies
            for component, assessment in zip(valid_components, assessments):
                screenshot_path = (
                    f"{screenshot_dir}/{component.component_id}.png"
                    if screenshot_dir
                    else None
                )

                component_discrepancies = (
                    self._agent.detect_discrepancies(
                        component, assessment, page_url, screenshot_path
                    )
                )

                discrepancies.extend(component_discrepancies)
                self._detected_discrepancies += len(component_discrepancies)
                self._processed_components += 1

        logger.info(
            "Batch component check complete",
            components_checked=len(valid_components),
            discrepancies_found=len(discrepancies),
        )

        return discrepancies

    def _aggregate_results(
        self,
        page: WebPage,
        components: List[WebComponent],
        assessments: List[ComparisonAssessment],
        discrepancies: List[Discrepancy],
    ) -> ComparisonResult:
        """Aggregate comparison results."""
        compliant_count = sum(
            1
            for a in assessments
            if a.status.value == "compliant"
        )

        avg_confidence = (
            sum(a.confidence for a in assessments) / len(assessments)
            if assessments
            else 0.0
        )

        critical_count = sum(
            1 for d in discrepancies if d.severity.value == "critical"
        )

        warning_count = sum(
            1 for d in discrepancies if d.severity.value == "warning"
        )

        return ComparisonResult(
            page_url=page.page_url,
            total_components=len(components),
            components_checked=len(assessments),
            compliant_components=compliant_count,
            non_compliant_components=len(assessments) - compliant_count,
            average_confidence=avg_confidence,
            discrepancies=discrepancies,
            critical_discrepancies=critical_count,
            warning_discrepancies=warning_count,
            comparison_timestamp=datetime.now(),
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "processed_components": self._processed_components,
            "detected_discrepancies": self._detected_discrepancies,
            "processing_errors": self._processing_errors,
            "agent_metrics": self._agent.get_metrics(),
        }

    def clear_caches(self) -> None:
        """Clear all internal caches."""
        self._agent.clear_cache()
        self._retriever.clear_cache()
        logger.info("All caches cleared")


logger.info("Compliance Orchestrator module loaded")
