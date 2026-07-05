"""
Unit tests for Compliance Orchestrator (Stage 9).

Tests end-to-end pipeline orchestration and result aggregation.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from src.agent.orchestrator import ComplianceOrchestrator
from src.data.models import (
    WebComponent,
    WebPage,
    ComponentType,
    GuidelineChunk,
    ComparisonContext,
    Discrepancy,
    SeverityLevel,
    DiscrepancyType,
    ComparisonResult,
)
from src.agent.compliance_agent import (
    ComparisonAssessment,
    ComparisonStatus,
)


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {
        "llm": {
            "model": "gpt-4",
            "temperature": 0.7,
        },
        "openai": {
            "api_key": "test-key",
        },
        "embeddings": {
            "model": "text-embedding-3-small",
        },
        "vector_db": {
            "type": "qdrant",
            "url": "http://localhost:6333",
        },
    }


@pytest.fixture
def orchestrator(mock_config):
    """Create orchestrator for testing."""
    with patch("src.agent.orchestrator.EmbeddingGenerator"):
        with patch("src.agent.orchestrator.QdrantVectorStore"):
            with patch("src.agent.orchestrator.SemanticRetriever"):
                with patch("src.agent.orchestrator.ContextBuilder"):
                    with patch("src.agent.orchestrator.ComplianceAgent"):
                        return ComplianceOrchestrator(mock_config)


@pytest.fixture
def sample_page():
    """Create sample web page."""
    return WebPage(
        page_id="page_1",
        page_url="https://example.com/login",
        page_title="Login Page",
        page_description="User authentication page",
        component_count=5,
    )


@pytest.fixture
def sample_components():
    """Create sample web components."""
    return [
        WebComponent(
            component_id="btn_1",
            component_type=ComponentType.BUTTON,
            selector="button.submit",
            actual_text="Submit",
            html_attributes={"type": "submit"},
            page_title="Login",
            page_url="https://example.com/login",
        ),
        WebComponent(
            component_id="input_1",
            component_type=ComponentType.INPUT,
            selector="input#username",
            actual_text="",
            html_attributes={"type": "text", "id": "username"},
            page_title="Login",
            page_url="https://example.com/login",
        ),
    ]


@pytest.fixture
def sample_guideline_chunks():
    """Create sample guideline chunks."""
    return [
        GuidelineChunk(
            chunk_id="chunk_1",
            text="All buttons must have descriptive text",
            section="Buttons",
            page_number=1,
            source_pdf="guidelines.pdf",
        ),
    ]


@pytest.fixture
def comparison_context(sample_components, sample_guideline_chunks):
    """Create comparison context."""
    return ComparisonContext(
        component=sample_components[0],
        relevant_guideline_chunks=sample_guideline_chunks,
        page_context="Login form",
    )


class TestOrchestratorInit:
    """Test Orchestrator initialization."""

    def test_init_success(self, mock_config):
        """Test successful initialization."""
        with patch("src.agent.orchestrator.EmbeddingGenerator"):
            with patch("src.agent.orchestrator.QdrantVectorStore"):
                with patch("src.agent.orchestrator.SemanticRetriever"):
                    with patch("src.agent.orchestrator.ContextBuilder"):
                        with patch("src.agent.orchestrator.ComplianceAgent"):
                            orch = ComplianceOrchestrator(mock_config)

                            assert orch._config == mock_config
                            assert orch._processed_components == 0
                            assert orch._detected_discrepancies == 0


class TestAggregateResults:
    """Test result aggregation."""

    def test_aggregate_results(self, orchestrator, sample_page, sample_components):
        """Test aggregating comparison results."""
        assessments = [
            ComparisonAssessment(
                component_id="btn_1",
                status=ComparisonStatus.COMPLIANT,
                confidence=0.95,
            ),
            ComparisonAssessment(
                component_id="input_1",
                status=ComparisonStatus.NON_COMPLIANT,
                confidence=0.8,
            ),
        ]

        discrepancies = [
            Discrepancy(
                discrepancy_id="disc_1",
                page_url=sample_page.page_url,
                component_id="input_1",
                component_type=ComponentType.INPUT,
                discrepancy_type=DiscrepancyType.MISSING,
                severity=SeverityLevel.WARNING,
                expected_value="label",
                actual_value="",
                guideline_citation="Section 2.1",
                reason="Missing label",
                recommendation="Add label",
                confidence=0.8,
                detected_at=datetime.now(),
            ),
        ]

        result = orchestrator._aggregate_results(
            sample_page, sample_components, assessments, discrepancies
        )

        assert isinstance(result, ComparisonResult)
        assert result.page_url == sample_page.page_url
        assert result.total_components == 2
        assert result.components_checked == 2
        assert result.compliant_components == 1
        assert result.non_compliant_components == 1
        assert len(result.discrepancies) == 1
        assert result.warning_discrepancies == 1


class TestAggregateResultsWithCritical:
    """Test result aggregation with critical severity."""

    def test_aggregate_with_critical_discrepancies(
        self, orchestrator, sample_page, sample_components
    ):
        """Test aggregation counts critical discrepancies."""
        assessments = [
            ComparisonAssessment(
                component_id="btn_1",
                status=ComparisonStatus.NON_COMPLIANT,
                confidence=0.9,
            ),
        ]

        discrepancies = [
            Discrepancy(
                discrepancy_id="disc_1",
                page_url=sample_page.page_url,
                component_id="btn_1",
                component_type=ComponentType.BUTTON,
                discrepancy_type=DiscrepancyType.MISSING,
                severity=SeverityLevel.CRITICAL,
                expected_value="required",
                actual_value="optional",
                guideline_citation="Section 1.1",
                reason="Critical attribute missing",
                recommendation="Add attribute",
                confidence=0.95,
                detected_at=datetime.now(),
            ),
        ]

        result = orchestrator._aggregate_results(
            sample_page, sample_components, assessments, discrepancies
        )

        assert result.critical_discrepancies == 1


class TestGetStatistics:
    """Test statistics retrieval."""

    def test_get_statistics(self, orchestrator):
        """Test getting orchestrator statistics."""
        # Simulate some processing
        orchestrator._processed_components = 10
        orchestrator._detected_discrepancies = 3
        orchestrator._processing_errors = 1

        stats = orchestrator.get_statistics()

        assert stats["processed_components"] == 10
        assert stats["detected_discrepancies"] == 3
        assert stats["processing_errors"] == 1
        assert "agent_metrics" in stats


class TestClearCaches:
    """Test cache clearing."""

    def test_clear_caches(self, orchestrator):
        """Test clearing all caches."""
        # Patch the clear_cache methods
        orchestrator._agent.clear_cache = Mock()
        orchestrator._retriever.clear_cache = Mock()

        orchestrator.clear_caches()

        orchestrator._agent.clear_cache.assert_called_once()
        orchestrator._retriever.clear_cache.assert_called_once()


class TestCheckPageAsync:
    """Test async page checking."""

    @pytest.mark.asyncio
    async def test_check_page_all_compliant(
        self, orchestrator, sample_page, sample_components, comparison_context
    ):
        """Test page check with all compliant components."""
        # Mock retriever
        orchestrator._retriever.retrieve_by_component = Mock(
            return_value=[
                Mock(chunk_id="chunk_1", text="Guideline")
            ]
        )

        # Mock context builder
        orchestrator._context_builder.build_comparison_context = Mock(
            return_value=comparison_context
        )

        # Mock agent
        assessment = ComparisonAssessment(
            component_id="btn_1",
            status=ComparisonStatus.COMPLIANT,
            confidence=0.95,
        )
        orchestrator._agent.compare_component = AsyncMock(
            return_value=assessment
        )
        orchestrator._agent.detect_discrepancies = Mock(return_value=[])

        # Check page
        result = await orchestrator.check_page(sample_page, sample_components)

        assert isinstance(result, ComparisonResult)
        assert result.compliant_components == 1
        assert len(result.discrepancies) == 0

    @pytest.mark.asyncio
    async def test_check_page_mixed_compliance(
        self, orchestrator, sample_page, sample_components, comparison_context
    ):
        """Test page check with mixed compliant/non-compliant."""
        # Mock retriever
        orchestrator._retriever.retrieve_by_component = Mock(
            return_value=[Mock(chunk_id="chunk_1")]
        )

        # Mock context builder
        orchestrator._context_builder.build_comparison_context = Mock(
            return_value=comparison_context
        )

        # Mock agent with different assessments
        assessments = [
            ComparisonAssessment(
                component_id="btn_1",
                status=ComparisonStatus.COMPLIANT,
                confidence=0.95,
            ),
            ComparisonAssessment(
                component_id="input_1",
                status=ComparisonStatus.NON_COMPLIANT,
                confidence=0.8,
            ),
        ]

        # Setup side_effect for multiple calls
        orchestrator._agent.compare_component = AsyncMock(
            side_effect=assessments
        )

        # Setup discrepancies
        discrepancy = Discrepancy(
            discrepancy_id="disc_1",
            page_url=sample_page.page_url,
            component_id="input_1",
            component_type=ComponentType.INPUT,
            discrepancy_type=DiscrepancyType.MISSING,
            severity=SeverityLevel.WARNING,
            expected_value="label",
            actual_value="",
            guideline_citation="Section 2.1",
            reason="Missing label",
            recommendation="Add label",
            confidence=0.8,
            detected_at=datetime.now(),
        )

        orchestrator._agent.detect_discrepancies = Mock(
            side_effect=[[], [discrepancy]]
        )

        # Check page
        result = await orchestrator.check_page(sample_page, sample_components)

        assert result.compliant_components == 1
        assert result.non_compliant_components == 1
        assert len(result.discrepancies) == 1


class TestCheckComponentsBatch:
    """Test batch component checking."""

    @pytest.mark.asyncio
    async def test_check_components_batch_success(
        self, orchestrator, sample_components, comparison_context
    ):
        """Test successful batch component checking."""
        page_url = "https://example.com/page"

        # Mock retriever
        orchestrator._retriever.retrieve_by_component = Mock(
            return_value=[Mock(chunk_id="chunk_1")]
        )

        # Mock context builder
        orchestrator._context_builder.build_comparison_context = Mock(
            return_value=comparison_context
        )

        # Mock agent
        assessments = [
            ComparisonAssessment(
                component_id="btn_1",
                status=ComparisonStatus.COMPLIANT,
                confidence=0.95,
            ),
            ComparisonAssessment(
                component_id="input_1",
                status=ComparisonStatus.COMPLIANT,
                confidence=0.9,
            ),
        ]

        orchestrator._agent.compare_components_batch = AsyncMock(
            return_value=assessments
        )

        orchestrator._agent.detect_discrepancies = Mock(return_value=[])

        # Check batch
        discrepancies = await orchestrator.check_components_batch(
            sample_components, page_url
        )

        assert len(discrepancies) == 0
        orchestrator._agent.compare_components_batch.assert_called_once()


class TestCheckComponentsBatchWithErrors:
    """Test batch checking with errors."""

    @pytest.mark.asyncio
    async def test_check_components_batch_with_failures(
        self, orchestrator, sample_components
    ):
        """Test batch processing continues on component failures."""
        page_url = "https://example.com/page"

        # Mock retriever to fail for first component
        orchestrator._retriever.retrieve_by_component = Mock(
            side_effect=[Exception("Retrieval failed"), Mock(chunk_id="chunk_1")]
        )

        orchestrator._context_builder.build_comparison_context = Mock()
        orchestrator._agent.compare_components_batch = AsyncMock(
            return_value=[]
        )

        # Check batch
        discrepancies = await orchestrator.check_components_batch(
            sample_components, page_url
        )

        # Should handle error and continue
        assert orchestrator._processing_errors > 0
