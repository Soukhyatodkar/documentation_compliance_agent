"""
Unit tests for Compliance Agent (Stage 9).

Tests LLM-powered comparison, discrepancy detection, and confidence scoring.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.agent.compliance_agent import (
    ComplianceAgent,
    ComparisonStatus,
    ComparisonAssessment,
)
from src.data.models import (
    WebComponent,
    ComponentType,
    GuidelineChunk,
    ComparisonContext,
    SeverityLevel,
    DiscrepancyType,
    Discrepancy,
)


@pytest.fixture
def mock_config():
    """Mock configuration for agent."""
    return {
        "llm": {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 1000,
        },
        "openai": {
            "api_key": "test-key-123",
        },
    }


@pytest.fixture
def agent(mock_config):
    """Create compliance agent for testing."""
    with patch("src.agent.compliance_agent.OpenAI"):
        with patch("src.agent.compliance_agent.AsyncOpenAI"):
            return ComplianceAgent(mock_config, use_async=True)


@pytest.fixture
def sample_component():
    """Create sample web component."""
    return WebComponent(
        component_id="btn_login",
        component_type=ComponentType.BUTTON,
        selector="button.login-btn",
        actual_text="Sign In",
        html_attributes={"class": "login-btn", "type": "button"},
        page_title="Login Page",
        page_url="https://example.com/login",
    )


@pytest.fixture
def sample_guideline_chunks():
    """Create sample guideline chunks."""
    return [
        GuidelineChunk(
            chunk_id="chunk_1",
            text="Buttons should use clear, action-oriented text.",
            section="UI Components",
            page_num=5,
            heading="Button Guidelines",
            embedding=[0.1, 0.2, 0.3] * 10,  # 30-dim embedding
        ),
        GuidelineChunk(
            chunk_id="chunk_2",
            text="Login buttons must be primary or secondary type.",
            section="UI Components",
            page_num=5,
            heading="Button Guidelines",
            embedding=[0.2, 0.3, 0.4] * 10,  # 30-dim embedding
        ),
    ]


@pytest.fixture
def comparison_context(sample_component, sample_guideline_chunks):
    """Create comparison context."""
    return ComparisonContext(
        component=sample_component,
        relevant_guideline_chunks=sample_guideline_chunks,
        page_context="User authentication form",
        query_used="login button",
    )


class TestComparisonAssessment:
    """Test ComparisonAssessment data class."""

    def test_creation(self):
        """Test assessment creation."""
        assessment = ComparisonAssessment(
            component_id="comp_1",
            status=ComparisonStatus.COMPLIANT,
            confidence=0.95,
            reason="Component follows guidelines",
        )

        assert assessment.component_id == "comp_1"
        assert assessment.status == ComparisonStatus.COMPLIANT
        assert assessment.confidence == 0.95

    def test_to_dict(self):
        """Test conversion to dictionary."""
        assessment = ComparisonAssessment(
            component_id="comp_1",
            status=ComparisonStatus.NON_COMPLIANT,
            confidence=0.8,
            reason="Missing required attribute",
            issues=["Missing label"],
            recommendations=["Add label element"],
        )

        result_dict = assessment.to_dict()

        assert result_dict["component_id"] == "comp_1"
        assert result_dict["status"] == "non_compliant"
        assert result_dict["confidence"] == 0.8
        assert len(result_dict["issues"]) == 1


class TestComplianceAgentInit:
    """Test ComplianceAgent initialization."""

    def test_init_success(self, mock_config):
        """Test successful initialization."""
        with patch("src.agent.compliance_agent.OpenAI"):
            with patch("src.agent.compliance_agent.AsyncOpenAI"):
                agent = ComplianceAgent(mock_config)

                assert agent._config == mock_config
                assert agent._total_comparisons == 0
                assert agent._comparison_cache == {}

    def test_init_missing_llm_config(self):
        """Test initialization with missing LLM config."""
        config = {"openai": {"api_key": "test-key"}}

        with patch("src.agent.compliance_agent.OpenAI"):
            with patch("src.agent.compliance_agent.AsyncOpenAI"):
                from src.core.exceptions import ConfigurationError

                with pytest.raises(ConfigurationError):
                    ComplianceAgent(config)

    def test_init_missing_openai_key(self):
        """Test initialization with missing OpenAI key."""
        config = {"llm": {"model": "gpt-4"}, "openai": {}}

        with patch("src.agent.compliance_agent.OpenAI"):
            with patch("src.agent.compliance_agent.AsyncOpenAI"):
                from src.core.exceptions import ConfigurationError

                with pytest.raises(ConfigurationError):
                    ComplianceAgent(config)


class TestBuildComparisonPrompt:
    """Test prompt building."""

    def test_build_comparison_prompt(self, agent, sample_component, comparison_context):
        """Test building comparison prompt."""
        prompt = agent._build_comparison_prompt(
            sample_component, comparison_context, include_examples=False
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert sample_component.actual_text in prompt
        assert "button" in prompt.lower()

    def test_prompt_includes_examples(self, agent, sample_component, comparison_context):
        """Test that examples can be included in prompt."""
        prompt_with_examples = agent._build_comparison_prompt(
            sample_component, comparison_context, include_examples=True
        )

        prompt_without = agent._build_comparison_prompt(
            sample_component, comparison_context, include_examples=False
        )

        assert len(prompt_with_examples) > len(prompt_without)


class TestFormatGuidelines:
    """Test guideline formatting."""

    def test_format_guidelines(self, agent, sample_guideline_chunks):
        """Test formatting guideline chunks."""
        formatted = agent._format_guidelines(sample_guideline_chunks)

        assert isinstance(formatted, str)
        assert "Section:" in formatted
        assert "Page:" in formatted
        assert len(formatted) > 0

    def test_format_empty_guidelines(self, agent):
        """Test formatting empty guideline list."""
        formatted = agent._format_guidelines([])

        assert formatted == ""


class TestParseComparisonResponse:
    """Test response parsing."""

    def test_parse_compliant_response(
        self, agent, sample_component, comparison_context
    ):
        """Test parsing compliant response."""
        response = """Compliant: YES
Confidence: 0.95
Reason: Component follows all guidelines
Issues: None
Recommendation: No changes needed
"""

        assessment = agent._parse_comparison_response(
            sample_component, comparison_context, response
        )

        assert assessment.status == ComparisonStatus.COMPLIANT
        assert assessment.confidence == 0.95
        assert "follows all guidelines" in assessment.reason

    def test_parse_non_compliant_response(
        self, agent, sample_component, comparison_context
    ):
        """Test parsing non-compliant response."""
        response = """Compliant: NO
Confidence: 0.8
Reason: Missing required accessibility attributes
Issues:
- Missing aria-label
- Color contrast insufficient
Recommendation: Add aria-label and increase contrast
"""

        assessment = agent._parse_comparison_response(
            sample_component, comparison_context, response
        )

        assert assessment.status == ComparisonStatus.NON_COMPLIANT
        assert assessment.confidence == 0.8
        assert len(assessment.issues) >= 1

    def test_parse_undetermined_response(
        self, agent, sample_component, comparison_context
    ):
        """Test parsing undetermined response."""
        response = "Cannot determine compliance from available information"

        assessment = agent._parse_comparison_response(
            sample_component, comparison_context, response
        )

        assert assessment.status == ComparisonStatus.NON_COMPLIANT  # Default
        assert assessment.raw_response == response


class TestDetermineSeverity:
    """Test severity determination."""

    def test_critical_severity(self, agent):
        """Test identification of critical issues."""
        issue = "Critical: Button functionality breaks the entire form"
        severity = agent._determine_severity(issue, None)

        assert severity == SeverityLevel.CRITICAL

    def test_warning_severity(self, agent):
        """Test identification of warning issues."""
        issue = "Warning: The button text should be more descriptive"
        severity = agent._determine_severity(issue, None)

        assert severity == SeverityLevel.WARNING

    def test_info_severity(self, agent):
        """Test identification of info-level issues."""
        issue = "The button could be styled differently"
        severity = agent._determine_severity(issue, None)

        assert severity == SeverityLevel.INFO


class TestMapIssueToType:
    """Test issue-to-type mapping."""

    def test_map_missing_issue(self, agent):
        """Test mapping missing issue."""
        issue = "Missing required aria-label attribute"
        issue_type = agent._map_issue_to_type(issue)

        assert issue_type == DiscrepancyType.MISSING

    def test_map_extra_issue(self, agent):
        """Test mapping extra issue."""
        issue = "Extra class attribute not mentioned in guidelines"
        issue_type = agent._map_issue_to_type(issue)

        assert issue_type == DiscrepancyType.EXTRA

    def test_map_incorrect_issue(self, agent):
        """Test mapping incorrect issue."""
        issue = "Button type is incorrect - should be primary not secondary"
        issue_type = agent._map_issue_to_type(issue)

        assert issue_type == DiscrepancyType.INCORRECT


class TestExtractExpectedValue:
    """Test expected value extraction."""

    def test_extract_from_quotes(self, agent):
        """Test extracting expected value from quotes."""
        issue = 'The text should be "Sign In" not "Login"'
        value = agent._extract_expected_value(issue)

        assert value == "Sign In"

    def test_extract_without_quotes(self, agent):
        """Test extracting when no quotes present."""
        issue = "Text is too short"
        value = agent._extract_expected_value(issue)

        assert value == "See guidelines"


class TestDetectDiscrepancies:
    """Test discrepancy detection."""

    def test_detect_discrepancies_compliant(
        self, agent, sample_component
    ):
        """Test that no discrepancies found for compliant component."""
        assessment = ComparisonAssessment(
            component_id=sample_component.component_id,
            status=ComparisonStatus.COMPLIANT,
            confidence=0.95,
        )

        discrepancies = agent.detect_discrepancies(
            sample_component,
            assessment,
            "https://example.com/page",
        )

        assert len(discrepancies) == 0

    def test_detect_discrepancies_non_compliant(
        self, agent, sample_component
    ):
        """Test discrepancy detection for non-compliant component."""
        assessment = ComparisonAssessment(
            component_id=sample_component.component_id,
            status=ComparisonStatus.NON_COMPLIANT,
            confidence=0.8,
            issues=["Missing aria-label", "Insufficient color contrast"],
            recommendations=["Add aria-label", "Increase contrast"],
            guideline_citations=["Section 2.1", "Section 3.2"],
        )

        discrepancies = agent.detect_discrepancies(
            sample_component,
            assessment,
            "https://example.com/page",
            screenshot_path="screenshots/btn_1.png",
        )

        assert len(discrepancies) == 2
        assert all(isinstance(d, Discrepancy) for d in discrepancies)
        assert discrepancies[0].screenshot_path == "screenshots/btn_1.png"


class TestCacheKey:
    """Test cache key generation."""

    def test_cache_key_generation(
        self, agent, sample_component, comparison_context
    ):
        """Test generating cache keys."""
        key1 = agent._get_cache_key(sample_component, comparison_context)
        key2 = agent._get_cache_key(sample_component, comparison_context)

        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) > 0


class TestMetrics:
    """Test metrics tracking."""

    def test_initial_metrics(self, agent):
        """Test initial metrics state."""
        metrics = agent.get_metrics()

        assert metrics["total_comparisons"] == 0
        assert metrics["successful_comparisons"] == 0
        assert metrics["failed_comparisons"] == 0
        assert metrics["cache_size"] == 0

    def test_metrics_after_cache(self, agent):
        """Test metrics include cache size."""
        # Manually add to cache
        assessment = ComparisonAssessment(
            component_id="test_1",
            status=ComparisonStatus.COMPLIANT,
        )
        agent._comparison_cache["test_key"] = assessment

        metrics = agent.get_metrics()
        assert metrics["cache_size"] == 1


class TestClearCache:
    """Test cache clearing."""

    def test_clear_cache(self, agent, sample_component, comparison_context):
        """Test clearing comparison cache."""
        # Add to cache
        cache_key = agent._get_cache_key(sample_component, comparison_context)
        assessment = ComparisonAssessment(
            component_id=sample_component.component_id,
            status=ComparisonStatus.COMPLIANT,
        )
        agent._comparison_cache[cache_key] = assessment

        assert len(agent._comparison_cache) == 1

        # Clear cache
        agent.clear_cache()

        assert len(agent._comparison_cache) == 0
