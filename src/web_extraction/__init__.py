"""
Web extraction module using Playwright.

Handles website navigation, authentication, component extraction,
and screenshot capture for automated compliance checking.

Main Classes:
- WebExtractor: Main orchestrator for website extraction
- AuthHandler: Authentication handling (form, basic, oauth2)
"""

from src.web_extraction.extractor import WebExtractor
from src.web_extraction.auth_handler import AuthHandler

__all__ = [
    "WebExtractor",
    "AuthHandler",
]
