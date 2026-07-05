"""
Compliance Agent - LLM-powered comparison and discrepancy detection.

This module provides the core compliance checking logic using LLM-based reasoning
to compare web components against guideline chunks and generate discrepancies.

Features:
- LLM-powered component vs. guideline comparison
- Discrepancy detection and categorization
- Confidence scoring
- Reasoning framework with citations
- Batch processing support
- Result caching and optimization
"""

import logging
import asyncio
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from openai import AsyncOpenAI, OpenAI
import structlog

from src.core.config import get_config
from src.core.exceptions import (
    ConfigurationError,
    ValidationError,
    ExternalAPIError,
)
from src.data.models import (
    WebComponent,
    GuidelineChunk,
    Discrepancy,
    DiscrepancyType,
    SeverityLevel,
    ComparisonContext,
    ComparisonResult,
)
from src.rag.prompts import CompliancePrompts, ContextualPrompts, FewShotPrompts
from src.utils.validators import ConfigValidator


logger = structlog.get_logger(__name__)


class ComparisonStatus(str, Enum):
    """Status of a comparison."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNDETERMINED = "undetermined"


@dataclass
class ComparisonAssessment:
    """Result of a single comparison."""

    component_id: str
    status: ComparisonStatus
    confidence: float = 0.0
    reason: str = ""
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    guideline_citations: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component_id": self.component_id,
            "status": self.status.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "guideline_citations": self.guideline_citations,
        }


class ComplianceAgent:
    """
    LLM-powered compliance checking agent.

    Compares web components against guidelines using OpenAI API.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        use_async: bool = True,
    ):
        """
        Initialize compliance agent.

        Args:
            config: Configuration dictionary. If None, loads from environment.
            use_async: Whether to use async OpenAI client.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        self._config = config or get_config()
        self._use_async = use_async

        # Validate config
        self._validate_config()

        # Initialize OpenAI client
        self._init_llm_client()

        # Cache for comparison results
        self._comparison_cache: Dict[str, ComparisonAssessment] = {}

        # Metrics
        self._total_comparisons = 0
        self._successful_comparisons = 0
        self._failed_comparisons = 0

        logger.info(
            "Compliance agent initialized",
            model=self._config.get("llm", {}).get("model", "gpt-4"),
            use_async=use_async,
        )

    def _validate_config(self) -> None:
        """Validate configuration."""
        required_keys = ["llm", "openai"]
        for key in required_keys:
            if key not in self._config:
                raise ConfigurationError(
                    f"Missing required config section: {key}"
                )

        llm_config = self._config.get("llm", {})
        if not llm_config.get("model"):
            raise ConfigurationError("LLM model not configured")

        openai_config = self._config.get("openai", {})
        if not openai_config.get("api_key"):
            raise ConfigurationError("OpenAI API key not configured")

    def _init_llm_client(self) -> None:
        """Initialize OpenAI client."""
        openai_config = self._config.get("openai", {})
        api_key = openai_config.get("api_key")

        if self._use_async:
            self._async_client = AsyncOpenAI(api_key=api_key)
        else:
            self._client = OpenAI(api_key=api_key)

    async def compare_component(
        self,
        component: WebComponent,
        context: ComparisonContext,
        include_examples: bool = True,
    ) -> ComparisonAssessment:
        """
        Compare a web component against guidelines.

        Args:
            component: Web component to compare.
            context: Comparison context with retrieved guidelines.
            include_examples: Whether to include few-shot examples.

        Returns:
            ComparisonAssessment with comparison results.

        Raises:
            ExternalAPIError: If LLM API call fails.
        """
        # Check cache
        cache_key = self._get_cache_key(component, context)
        if cache_key in self._comparison_cache:
            logger.debug(
                "Using cached comparison",
                component_id=component.component_id,
            )
            return self._comparison_cache[cache_key]

        # Build prompt
        prompt = self._build_comparison_prompt(
            component, context, include_examples
        )

        # Call LLM
        try:
            response = await self._call_llm(prompt)
        except Exception as e:
            logger.error(
                "LLM comparison failed",
                component_id=component.component_id,
                error=str(e),
            )
            self._failed_comparisons += 1
            raise ExternalAPIError(f"LLM comparison failed: {e}") from e

        # Parse response
        assessment = self._parse_comparison_response(
            component, context, response
        )

        # Cache result
        self._comparison_cache[cache_key] = assessment

        # Update metrics
        self._total_comparisons += 1
        if assessment.status != ComparisonStatus.UNDETERMINED:
            self._successful_comparisons += 1

        logger.debug(
            "Comparison completed",
            component_id=component.component_id,
            status=assessment.status.value,
            confidence=assessment.confidence,
        )

        return assessment

    async def compare_components_batch(
        self,
        components: List[WebComponent],
        contexts: List[ComparisonContext],
        max_concurrent: int = 5,
    ) -> List[ComparisonAssessment]:
        """
        Compare multiple components concurrently.

        Args:
            components: List of web components.
            contexts: List of comparison contexts.
            max_concurrent: Maximum concurrent comparisons.

        Returns:
            List of ComparisonAssessment objects.

        Raises:
            ValidationError: If lists have different lengths.
        """
        if len(components) != len(contexts):
            raise ValidationError(
                "Components and contexts must have same length"
            )

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _compare_with_semaphore(
            comp: WebComponent, ctx: ComparisonContext
        ) -> ComparisonAssessment:
            async with semaphore:
                return await self.compare_component(comp, ctx)

        # Run comparisons concurrently
        assessments = await asyncio.gather(
            *[
                _compare_with_semaphore(comp, ctx)
                for comp, ctx in zip(components, contexts)
            ]
        )

        return assessments

    def detect_discrepancies(
        self,
        component: WebComponent,
        assessment: ComparisonAssessment,
        page_url: str,
        screenshot_path: Optional[str] = None,
    ) -> List[Discrepancy]:
        """
        Detect discrepancies from comparison assessment.

        Args:
            component: Original web component.
            assessment: Comparison assessment.
            page_url: URL of the page containing component.
            screenshot_path: Optional path to screenshot evidence.

        Returns:
            List of Discrepancy objects.
        """
        discrepancies: List[Discrepancy] = []

        if assessment.status == ComparisonStatus.COMPLIANT:
            return discrepancies

        # Create discrepancy for each issue
        for i, issue in enumerate(assessment.issues):
            severity = self._determine_severity(issue, assessment)

            discrepancy = Discrepancy(
                discrepancy_id=f"{component.component_id}_issue_{i}",
                page_url=page_url,
                component_id=component.component_id,
                component_type=component.component_type,
                discrepancy_type=self._map_issue_to_type(issue),
                severity=severity,
                expected_value=self._extract_expected_value(issue),
                actual_value=component.actual_text or component.selector,
                guideline_citation=assessment.guideline_citations[i]
                if i < len(assessment.guideline_citations)
                else "See guidelines",
                reason=issue,
                recommendation=assessment.recommendations[i]
                if i < len(assessment.recommendations)
                else "Review guidelines for required changes",
                confidence=assessment.confidence,
                detected_at=datetime.now(),
                screenshot_path=screenshot_path,
            )

            discrepancies.append(discrepancy)

        return discrepancies

    def _build_comparison_prompt(
        self,
        component: WebComponent,
        context: ComparisonContext,
        include_examples: bool,
    ) -> str:
        """Build LLM prompt for comparison."""
        # Get contextual prompt if available
        contextual = ContextualPrompts.get_contextual_prompt(
            component.component_type.value
        )

        if contextual:
            base_prompt = contextual
        else:
            base_prompt = CompliancePrompts.COMPARISON_PROMPT.template

        # Format with values
        guideline_text = self._format_guidelines(context.relevant_guideline_chunks)

        prompt = base_prompt.format(
            component_type=component.component_type.value,
            component_text=component.actual_text or component.selector,
            component_selector=component.selector,
            guidelines=guideline_text,
        )

        # Add few-shot examples if requested
        if include_examples:
            prompt = FewShotPrompts.add_examples_to_prompt(prompt)

        return prompt

    def _format_guidelines(self, chunks: List[GuidelineChunk]) -> str:
        """Format guideline chunks for LLM."""
        formatted = []

        for chunk in chunks:
            section = chunk.section or "General"
            text = (
                f"[Section: {section}] "
                f"[Page: {chunk.page_num}] "
                f"{chunk.text}"
            )
            formatted.append(text)

        return "\n\n".join(formatted)

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt."""
        llm_config = self._config.get("llm", {})
        model = llm_config.get("model", "gpt-4")
        temperature = llm_config.get("temperature", 0.7)
        max_tokens = llm_config.get("max_tokens", 1000)

        if self._use_async:
            response = await self._async_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert compliance auditor. "
                        "Analyze components against guidelines carefully.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert compliance auditor. "
                        "Analyze components against guidelines carefully.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

        return response.choices[0].message.content

    def _parse_comparison_response(
        self,
        component: WebComponent,
        context: ComparisonContext,
        response: str,
    ) -> ComparisonAssessment:
        """Parse LLM response into ComparisonAssessment."""
        assessment = ComparisonAssessment(
            component_id=component.component_id,
            status=ComparisonStatus.UNDETERMINED,
            raw_response=response,
        )

        # Extract status
        if "compliant: yes" in response.lower():
            assessment.status = ComparisonStatus.COMPLIANT
        elif "compliant: no" in response.lower():
            assessment.status = ComparisonStatus.NON_COMPLIANT
        else:
            # Default to non-compliant if unclear
            assessment.status = ComparisonStatus.NON_COMPLIANT

        # Extract confidence
        confidence_match = None
        for line in response.split("\n"):
            if "confidence:" in line.lower():
                try:
                    # Try to extract float between 0 and 1
                    parts = line.split(":")
                    if len(parts) > 1:
                        value_str = parts[1].strip().split()[0]
                        confidence = float(value_str)
                        if 0 <= confidence <= 1:
                            assessment.confidence = confidence
                        break
                except (ValueError, IndexError):
                    pass

        if assessment.confidence == 0.0:
            # Default confidence based on status
            assessment.confidence = (
                0.9 if assessment.status == ComparisonStatus.COMPLIANT else 0.7
            )

        # Extract reason
        for line in response.split("\n"):
            if "reason:" in line.lower():
                assessment.reason = line.split(":", 1)[1].strip()
                break

        # Extract issues
        in_issues = False
        for line in response.split("\n"):
            if "issues:" in line.lower():
                in_issues = True
                continue
            if in_issues and line.strip().startswith(("-", "*", "•", "·")):
                issue = line.strip().lstrip("-*•· ").strip()
                if issue:
                    assessment.issues.append(issue)
            elif in_issues and line.strip() and not line.strip()[0].isalnum():
                continue
            elif in_issues and line.strip() and line.strip()[0].isalnum():
                in_issues = False

        # Extract recommendations
        in_recommendations = False
        for line in response.split("\n"):
            if "recommendation:" in line.lower():
                in_recommendations = True
                continue
            if in_recommendations and line.strip():
                assessment.recommendations.append(line.strip())

        # Add guideline citations
        for chunk in context.relevant_guideline_chunks:
            if chunk.section:
                assessment.guideline_citations.append(
                    f"Section {chunk.section}, Page {chunk.page_number}"
                )

        return assessment

    def _get_cache_key(
        self, component: WebComponent, context: ComparisonContext
    ) -> str:
        """Generate cache key for comparison."""
        component_key = f"{component.component_id}_{component.actual_text or ''}"
        chunks_key = "_".join(
            [chunk.chunk_id for chunk in context.relevant_guideline_chunks]
        )
        return f"{component_key}_{chunks_key}"

    def _determine_severity(
        self, issue: str, assessment: ComparisonAssessment
    ) -> SeverityLevel:
        """Determine severity level from issue description."""
        issue_lower = issue.lower()

        if any(
            word in issue_lower
            for word in [
                "critical",
                "must",
                "required",
                "essential",
                "mandatory",
                "breaks",
                "fails",
            ]
        ):
            return SeverityLevel.CRITICAL

        if any(
            word in issue_lower
            for word in [
                "should",
                "important",
                "significant",
                "issue",
                "problem",
            ]
        ):
            return SeverityLevel.WARNING

        return SeverityLevel.INFO

    def _map_issue_to_type(self, issue: str) -> DiscrepancyType:
        """Map issue description to discrepancy type."""
        issue_lower = issue.lower()

        # Check for specific words in specific order (more specific first)
        if any(
            word in issue_lower
            for word in ["incorrect", "wrong", "mismatch", "doesn't match"]
        ):
            return DiscrepancyType.INCORRECT

        if any(
            word in issue_lower for word in ["extra", "additional", "unexpected"]
        ):
            return DiscrepancyType.EXTRA

        if any(word in issue_lower for word in ["missing", "absent", "required"]):
            return DiscrepancyType.MISSING

        return DiscrepancyType.OTHER

    def _extract_expected_value(self, issue: str) -> str:
        """Extract expected value from issue description."""
        # Simple heuristic: look for quotes or specific patterns
        if '"' in issue:
            parts = issue.split('"')
            if len(parts) >= 3:
                return parts[1]

        return "See guidelines"

    def clear_cache(self) -> None:
        """Clear comparison cache."""
        self._comparison_cache.clear()
        logger.info("Comparison cache cleared")

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics."""
        return {
            "total_comparisons": self._total_comparisons,
            "successful_comparisons": self._successful_comparisons,
            "failed_comparisons": self._failed_comparisons,
            "cache_size": len(self._comparison_cache),
            "success_rate": (
                self._successful_comparisons / self._total_comparisons
                if self._total_comparisons > 0
                else 0.0
            ),
        }


logger.info("Compliance Agent module loaded")
