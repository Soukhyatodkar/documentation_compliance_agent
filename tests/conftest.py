"""
Pytest configuration and shared fixtures for the test suite.

This module provides common fixtures and configuration used across
all unit and integration tests.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def event_loop():
    """Provide event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir(tmp_path) -> Path:
    """Provide temporary directory for test files."""
    return tmp_path


@pytest.fixture
def mock_config():
    """Provide mock configuration object."""
    config = {
        "website": {
            "url": "https://example.com",
            "authentication": {"type": "none"},
            "crawling": {"max_pages": 10, "max_links": 50},
        },
        "pdf": {
            "path": "data/pdfs/test_guidelines.pdf",
            "chunking": {"min_chunk_size": 100, "max_chunk_size": 1000, "overlap": 100},
        },
        "llm": {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
        },
        "vector_db": {
            "url": "http://localhost:6333",
            "collection_name": "test_guidelines",
        },
        "output": {
            "base_dir": "data",
            "reports_dir": "data/reports",
            "screenshots_dir": "data/screenshots",
        },
        "logging": {
            "level": "DEBUG",
            "file": "logs/test.log",
        },
    }
    return config


@pytest.fixture
def mock_page_data():
    """Provide mock extracted page data."""
    return {
        "page_url": "https://example.com/features",
        "page_title": "Our Features",
        "screenshot_path": "data/screenshots/page_1.png",
        "components": [
            {
                "type": "heading",
                "selector": ".page-title",
                "text": "Our Features",
                "level": 1,
            },
            {
                "type": "button",
                "selector": ".cta-button",
                "text": "Get Started",
                "url": "https://example.com/signup",
            },
            {
                "type": "text",
                "selector": ".description",
                "text": "Browse our amazing features",
            },
        ],
        "extracted_at": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def mock_guideline_data():
    """Provide mock guideline data."""
    return {
        "page_title": "Features Page",
        "expected_components": [
            {
                "type": "heading",
                "expected_text": "Features",
                "level": 1,
                "section": "2.1",
            },
            {
                "type": "button",
                "expected_text": "Get Started",
                "section": "2.3",
            },
        ],
        "layout_guidelines": {
            "header_required": True,
            "footer_required": True,
            "sidebar": False,
        },
        "section": "Page 15-17",
    }


@pytest.fixture
def mock_discrepancy():
    """Provide mock discrepancy object."""
    return {
        "page_url": "https://example.com/features",
        "component": "heading",
        "actual_text": "Our Features",
        "expected_text": "Features",
        "guideline_citation": "Section 2.1",
        "severity": "warning",
        "confidence": 0.92,
        "reason": "Text content does not match guideline",
        "screenshot_path": "data/screenshots/page_1.png",
    }


@pytest.fixture
def mock_openai_response():
    """Provide mock OpenAI API response."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1705326600,
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "The heading text differs from the guideline specification.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 50,
            "total_tokens": 200,
        },
    }


@pytest.fixture
def mock_embeddings_response():
    """Provide mock embeddings API response."""
    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "embedding": [
                    0.1,
                    0.2,
                    0.3,
                    -0.1,
                    0.15,
                ] * 307,  # 1536 dimensions
                "index": 0,
            }
        ],
        "model": "text-embedding-3-small",
        "usage": {"prompt_tokens": 8, "total_tokens": 8},
    }


@pytest.fixture
def mock_qdrant_response():
    """Provide mock Qdrant search response."""
    return [
        {
            "id": "chunk_1",
            "score": 0.92,
            "payload": {
                "text": "Features section describes available features",
                "page": 15,
                "section": "2.1",
                "heading": "Features",
            },
        },
        {
            "id": "chunk_2",
            "score": 0.85,
            "payload": {
                "text": "Header should clearly label page content",
                "page": 8,
                "section": "1.2",
                "heading": "Headers",
            },
        },
    ]
