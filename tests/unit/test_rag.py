"""
Unit tests for RAG pipeline components.

Tests query processing and context building (core components).
"""

import pytest
from src.rag.queries import QueryProcessor, QueryExpander, QueryAnalyzer
from src.data.models import GuidelineChunk, WebComponent, ComponentType, ComparisonContext
from src.rag.context import ContextBuilder, FormattedContext
from src.rag.prompts import CompliancePrompts, ContextualPrompts


class TestQueryProcessor:
    """Test QueryProcessor."""

    def test_normalize_query(self):
        """Test query normalization."""
        processor = QueryProcessor()
        
        query = "   Login    authentication   "
        normalized = processor.normalize_query(query)
        
        assert "login" in normalized.lower()
        assert len(normalized.split()) >= 1

    def test_process_text(self):
        """Test text processing."""
        processor = QueryProcessor()
        
        text = "This is a test query with too many spaces   and    special!@#"
        processed = processor.process_text(text)
        
        assert isinstance(processed, str)
        assert len(processed) > 0

    def test_extract_keyphrases(self):
        """Test keyphrase extraction."""
        processor = QueryProcessor()
        
        text = "The login button should be primary and required for authentication"
        keyphrases = processor.extract_keyphrases(text, top_k=3)
        
        assert isinstance(keyphrases, list)
        assert len(keyphrases) <= 3

    def test_split_into_subqueries(self):
        """Test query splitting."""
        processor = QueryProcessor()
        
        query = "login and authentication or signin"
        subqueries = processor.split_into_subqueries(query)
        
        assert len(subqueries) >= 1


class TestQueryExpander:
    """Test QueryExpander."""

    def test_expand_query(self):
        """Test query expansion."""
        expander = QueryExpander()
        
        query = "login button"
        expansions = expander.expand_query(query)
        
        assert len(expansions) >= 1
        assert query in expansions

    def test_generate_variations(self):
        """Test generating variations."""
        expander = QueryExpander()
        
        component = WebComponent(
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            selector="button.primary",
            actual_text="Login",
        )
        
        variations = expander.generate_variations(component)
        
        assert len(variations) >= 1
        assert all(isinstance(v, str) for v in variations)


class TestQueryAnalyzer:
    """Test QueryAnalyzer."""

    def test_analyze_query(self):
        """Test query analysis."""
        query = "login button should be required"
        analysis = QueryAnalyzer.analyze_query(query)
        
        assert "length" in analysis
        assert "word_count" in analysis
        assert "has_keywords" in analysis

    def test_compare_queries(self):
        """Test query comparison."""
        query1 = "login authentication button"
        query2 = "login button"
        
        similarity = QueryAnalyzer.compare_queries(query1, query2)
        
        assert 0 <= similarity <= 1
        assert similarity > 0

    def test_deduplicate_queries(self):
        """Test query deduplication."""
        queries = [
            "login button",
            "login button required",
            "different query",
            "login button",
        ]
        
        dedup = QueryAnalyzer.deduplicate_queries(queries, threshold=0.7)
        
        assert len(dedup) <= len(queries)


class TestContextBuilder:
    """Test ContextBuilder."""

    def test_normalize_query_simple(self):
        """Test simple query normalization."""
        builder = ContextBuilder()
        
        chunk = GuidelineChunk(
            chunk_id="chunk_1",
            text="Login buttons should be primary action buttons",
            page_num=1,
            section="Buttons",
            heading="Primary Actions",
            embedding=[0.1] * 1536,
        )
        
        component = WebComponent(
            component_id="comp_1",
            component_type=ComponentType.BUTTON,
            selector="button.primary",
            actual_text="Login",
        )
        
        # Just verify builder can be instantiated and methods exist
        assert hasattr(builder, 'build_context')
        assert hasattr(builder, 'build_comparison_context')


class TestPromptTemplates:
    """Test prompt templates."""

    def test_compliance_prompt_exists(self):
        """Test compliance prompt template."""
        prompt = CompliancePrompts.COMPARISON_PROMPT
        
        assert prompt is not None
        assert isinstance(prompt.template, str)
        assert "{component_type}" in prompt.template

    def test_get_prompt(self):
        """Test getting prompts by name."""
        prompt = CompliancePrompts.get_prompt("comparison")
        
        assert prompt is not None
        assert prompt.name == "comparison"

    def test_contextual_prompt_button(self):
        """Test contextual prompt for button."""
        prompt = ContextualPrompts.get_contextual_prompt("button")
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert "button" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
