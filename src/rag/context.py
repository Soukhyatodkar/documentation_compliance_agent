"""
Context building for RAG pipeline.

Formats retrieved guideline chunks into context for LLM comparison.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.rag.retriever import RetrievalResult
from src.data.models import GuidelineChunk, WebComponent, ComparisonContext


logger = logging.getLogger(__name__)


@dataclass
class FormattedContext:
    """Formatted context for LLM."""

    text: str
    chunk_count: int
    token_estimate: int
    sections: List[str]
    page_range: tuple
    metadata: Dict[str, Any]


class ContextBuilder:
    """Build and format context for LLM-based comparison."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize context builder."""
        self.config = config or {}
        self.max_context_length = self.config.get("max_context_length", 2000)
        self.include_page_numbers = self.config.get("include_page_numbers", True)
        self.include_sections = self.config.get("include_sections", True)
        self.include_metadata = self.config.get("include_metadata", True)
        self.separator = self.config.get("separator", "\n---\n")
        
        logger.info("Initialized context builder")

    def build_context(
        self,
        retrieval_results: List[RetrievalResult],
        component: WebComponent,
        page_context: Optional[str] = None,
        max_length: Optional[int] = None,
    ) -> FormattedContext:
        """Build formatted context from retrieval results."""
        try:
            max_length = max_length or self.max_context_length
            
            # Extract chunks
            chunks = [r.chunk for r in retrieval_results]
            
            # Format chunks
            formatted_text = self._format_chunks(chunks, max_length)
            
            # Add page context if provided
            if page_context:
                formatted_text = self._add_page_context(formatted_text, page_context)
            
            # Calculate metadata
            sections = list(set(
                c.section for c in chunks if c.section
            ))
            pages = [c.page_num for c in chunks]
            page_range = (min(pages), max(pages)) if pages else (0, 0)
            
            # Token estimation (rough)
            token_estimate = len(formatted_text.split()) // 4 + 100
            
            context = FormattedContext(
                text=formatted_text,
                chunk_count=len(chunks),
                token_estimate=token_estimate,
                sections=sections,
                page_range=page_range,
                metadata={
                    "component_id": component.component_id,
                    "component_type": component.component_type.value
                    if hasattr(component.component_type, "value")
                    else str(component.component_type),
                    "actual_text": component.actual_text,
                    "selector": component.selector,
                },
            )
            
            logger.debug(
                f"Built context with {len(chunks)} chunks "
                f"({token_estimate} tokens estimated)"
            )
            
            return context
        
        except Exception as e:
            logger.error(f"Failed to build context: {e}")
            raise

    def build_comparison_context(
        self,
        component: WebComponent,
        retrieval_results: List[RetrievalResult],
        page_context: Optional[str] = None,
        comparison_instructions: Optional[str] = None,
    ) -> ComparisonContext:
        """Build ComparisonContext for LLM agent."""
        try:
            # Build formatted context
            formatted = self.build_context(
                retrieval_results,
                component,
                page_context,
            )
            
            # Convert formatted chunks to GuidelineChunk objects
            relevant_chunks = [r.chunk for r in retrieval_results]
            
            # Build instructions
            if not comparison_instructions:
                comparison_instructions = self._generate_default_instructions(
                    component,
                    len(relevant_chunks),
                )
            
            context = ComparisonContext(
                component=component,
                relevant_guideline_chunks=relevant_chunks,
                page_context=page_context or formatted.text,
                comparison_instructions=comparison_instructions,
            )
            
            logger.debug(f"Built comparison context for {component.component_id}")
            
            return context
        
        except Exception as e:
            logger.error(f"Failed to build comparison context: {e}")
            raise

    def _format_chunks(
        self,
        chunks: List[GuidelineChunk],
        max_length: int,
    ) -> str:
        """Format chunks into readable text."""
        parts = []
        current_length = 0
        
        for chunk in chunks:
            # Format chunk
            formatted_chunk = self._format_single_chunk(chunk)
            chunk_length = len(formatted_chunk)
            
            # Check length
            if current_length + chunk_length > max_length:
                # Truncate chunk if necessary
                remaining = max_length - current_length
                if remaining > 100:  # Only include if meaningful
                    formatted_chunk = formatted_chunk[:remaining] + "..."
                    parts.append(formatted_chunk)
                break
            
            parts.append(formatted_chunk)
            current_length += chunk_length + len(self.separator)
        
        return self.separator.join(parts)

    def _format_single_chunk(self, chunk: GuidelineChunk) -> str:
        """Format single chunk for display."""
        parts = []
        
        # Add section and heading
        if self.include_sections:
            if chunk.section:
                parts.append(f"[Section: {chunk.section}]")
            if chunk.heading:
                parts.append(f"**{chunk.heading}**")
        
        # Add page number
        if self.include_page_numbers:
            parts.append(f"(Page {chunk.page_num})")
        
        # Add text
        parts.append(chunk.text)
        
        return "\n".join(parts)

    def _add_page_context(self, context: str, page_context: str) -> str:
        """Add page context to formatted chunks."""
        return f"Page Context:\n{page_context}\n\nRelated Guidelines:\n{context}"

    def _generate_default_instructions(
        self,
        component: WebComponent,
        chunk_count: int,
    ) -> str:
        """Generate default comparison instructions."""
        return (
            f"Compare the following web component against {chunk_count} guideline chunks. "
            f"Component type: {component.component_type}. "
            f"Component text: '{component.actual_text}'. "
            f"Determine if the component complies with the guidelines, "
            f"identify any discrepancies, and provide a confidence score."
        )


class ContextFormatter:
    """Format context for different LLM models."""

    @staticmethod
    def format_for_gpt(
        context: FormattedContext,
        component: WebComponent,
        task: str = "comparison",
    ) -> str:
        """Format context for GPT models."""
        prompt = f"""You are a compliance verification agent. Your task is to {task}.

## Component Information
Type: {context.metadata.get('component_type', 'unknown')}
Text: {context.metadata.get('actual_text', 'N/A')}
Selector: {context.metadata.get('selector', 'N/A')}

## Relevant Guidelines
{context.text}

## Pages Referenced
Pages {context.page_range[0]} to {context.page_range[1]}

## Your Task
Analyze if the component complies with the provided guidelines. 
Provide your reasoning and a confidence score (0-1).
"""
        return prompt

    @staticmethod
    def format_for_claude(
        context: FormattedContext,
        component: WebComponent,
        task: str = "comparison",
    ) -> str:
        """Format context for Claude models."""
        prompt = f"""<task>
You are a compliance verification expert. Your task is to {task}.
</task>

<component_info>
<type>{context.metadata.get('component_type', 'unknown')}</type>
<text>{context.metadata.get('actual_text', 'N/A')}</text>
<selector>{context.metadata.get('selector', 'N/A')}</selector>
</component_info>

<guidelines>
{context.text}
</guidelines>

<page_range>Pages {context.page_range[0]} to {context.page_range[1]}</page_range>

<instructions>
Analyze the component against the provided guidelines.
- Identify any compliance issues
- Determine if the component matches guideline requirements
- Provide reasoning for your assessment
- Give a confidence score (0-1) for your assessment
</instructions>
"""
        return prompt

    @staticmethod
    def format_for_local_llm(
        context: FormattedContext,
        component: WebComponent,
        task: str = "comparison",
    ) -> str:
        """Format context for local LLM models."""
        prompt = f"""Task: {task}

Component:
- Type: {context.metadata.get('component_type', 'unknown')}
- Text: {context.metadata.get('actual_text', 'N/A')}
- Selector: {context.metadata.get('selector', 'N/A')}

Guidelines:
{context.text}

Question: Does this component comply with the guidelines?
Answer (include reasoning and confidence score):
"""
        return prompt


class ContextOptimizer:
    """Optimize context for token efficiency."""

    @staticmethod
    def compress_context(
        context: FormattedContext,
        target_tokens: int = 512,
    ) -> FormattedContext:
        """Compress context to fit within token limit."""
        current_tokens = context.token_estimate
        
        if current_tokens <= target_tokens:
            return context
        
        # Calculate compression ratio
        ratio = target_tokens / current_tokens
        target_length = int(len(context.text) * ratio)
        
        # Truncate text
        compressed_text = context.text[:target_length]
        if len(context.text) > target_length:
            compressed_text += "...[truncated]"
        
        return FormattedContext(
            text=compressed_text,
            chunk_count=context.chunk_count,
            token_estimate=target_tokens,
            sections=context.sections,
            page_range=context.page_range,
            metadata=context.metadata,
        )

    @staticmethod
    def expand_context(
        context: FormattedContext,
        surrounding_chunks: List[GuidelineChunk],
    ) -> FormattedContext:
        """Expand context with surrounding chunks."""
        # Add surrounding context
        expanded_text = context.text
        
        for chunk in surrounding_chunks[:3]:  # Add up to 3 surrounding
            chunk_text = f"\n[Related] {chunk.text}\n"
            expanded_text += chunk_text
        
        # Recalculate token estimate
        token_estimate = len(expanded_text.split()) // 4 + 100
        
        return FormattedContext(
            text=expanded_text,
            chunk_count=context.chunk_count + len(surrounding_chunks),
            token_estimate=token_estimate,
            sections=context.sections,
            page_range=context.page_range,
            metadata=context.metadata,
        )

    @staticmethod
    def rerank_for_relevance(
        context: FormattedContext,
        keyword: str,
    ) -> FormattedContext:
        """Reorder context chunks by keyword relevance."""
        # Split context by separator
        chunks = context.text.split("\n---\n")
        
        # Score chunks
        scored = [
            (chunk, chunk.lower().count(keyword.lower()))
            for chunk in chunks
        ]
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Rejoin
        reranked_text = "\n---\n".join([c[0] for c in scored])
        
        return FormattedContext(
            text=reranked_text,
            chunk_count=context.chunk_count,
            token_estimate=context.token_estimate,
            sections=context.sections,
            page_range=context.page_range,
            metadata=context.metadata,
        )
