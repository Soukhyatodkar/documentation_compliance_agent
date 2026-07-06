# Web Extraction Implementation Guide

> **Quick guide to implement the missing Playwright-based web extraction module**

**Estimated Time:** 4-6 hours  
**Complexity:** Medium  
**Priority:** CRITICAL (blocks end-to-end pipeline)

---

## Overview

The web extraction module is currently a stub. This guide walks you through implementing it to complete the project.

### What You Need to Build

```
Web Extraction Pipeline
    ↓
1. Initialize Playwright browser
2. Authenticate (if required)
3. Navigate pages (following links)
4. Extract components
5. Capture screenshots
6. Store structured data
```

---

## Implementation Plan

### Step 1: Create Core Extractor Class

**File:** `src/web_extraction/extractor.py`

```python
"""
Main website extraction orchestrator using Playwright.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import structlog

from src.core.models import Config
from src.core.exceptions import WebExtractionError, AuthenticationError
from src.data.models import WebComponent, WebPage, WebsiteExtraction
from src.coverage.tracker import CoverageTracker

logger = structlog.get_logger(__name__)


class WebExtractor:
    """Extract web components using Playwright."""

    def __init__(self, config: Config, coverage_tracker: Optional[CoverageTracker] = None):
        """Initialize web extractor."""
        self.config = config
        self.coverage_tracker = coverage_tracker
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.visited_urls: Set[str] = set()
        self.extraction_id = f"extraction_{datetime.now().isoformat()}"
        
        logger.info(f"Initialized WebExtractor: {self.extraction_id}")

    async def extract_website(self) -> WebsiteExtraction:
        """Extract entire website."""
        try:
            await self._init_browser()
            
            # Start with homepage
            pages = []
            urls_to_visit = [self.config.website.url]
            max_pages = self.config.website.crawling.max_pages
            
            while urls_to_visit and len(pages) < max_pages:
                url = urls_to_visit.pop(0)
                
                if url in self.visited_urls:
                    continue
                
                try:
                    page_data = await self.extract_page(url)
                    if page_data:
                        pages.append(page_data)
                        
                        # Extract new URLs for crawling
                        new_urls = await self._get_links_from_page(self.page)
                        urls_to_visit.extend([u for u in new_urls if u not in self.visited_urls])
                
                except Exception as e:
                    logger.error(f"Failed to extract {url}: {str(e)}")
                    if self.coverage_tracker:
                        self.coverage_tracker.fail_page(url, str(e))
            
            # Create extraction result
            return WebsiteExtraction(
                extraction_id=self.extraction_id,
                website_url=self.config.website.url,
                pages=pages,
                total_pages_extracted=len(pages),
                total_pages_attempted=len(self.visited_urls),
                started_at=datetime.now().isoformat()
            )
            
        finally:
            await self._close_browser()

    async def extract_page(self, url: str) -> Optional[WebPage]:
        """Extract single page."""
        try:
            # Navigate to page
            await self.page.goto(url, wait_until="networkidle")
            self.visited_urls.add(url)
            
            if self.coverage_tracker:
                self.coverage_tracker.start_page(url, f"page_{len(self.visited_urls)}")
            
            # Wait for dynamic content
            if self.config.website.extraction.wait_for_selectors:
                for selector in self.config.website.extraction.wait_for_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                    except:
                        pass  # Selector not found, continue
            
            # Execute custom JavaScript if configured
            if self.config.website.extraction.execute_js:
                await self.page.evaluate(self.config.website.extraction.execute_js)
            
            # Handle scrolling
            if self.config.website.extraction.scroll_behavior != "none":
                await self._scroll_page()
            
            # Extract page metadata
            title = await self.page.title()
            description = await self.page.locator('meta[name="description"]').get_attribute("content")
            
            # Extract all text
            page_text = await self.page.locator("body").text_content()
            
            # Extract components
            components = await self._extract_components()
            
            # Take screenshot
            screenshot_path = None
            if self.config.browser.screenshots.enabled:
                screenshot_path = await self._take_screenshot(url)
            
            # Create page object
            page_data = WebPage(
                page_id=f"page_{len(self.visited_urls)}",
                url=url,
                title=title,
                description=description,
                page_text=page_text or "",
                components=components,
                screenshot_path=screenshot_path,
                extracted_at=datetime.now().isoformat(),
            )
            
            if self.coverage_tracker:
                self.coverage_tracker.succeed_page(
                    url,
                    components_count=len(components),
                    text_length=len(page_text or ""),
                    title=title,
                    screenshot_taken=screenshot_path is not None
                )
            
            logger.info(f"Extracted page {url}: {len(components)} components")
            return page_data
            
        except Exception as e:
            logger.error(f"Failed to extract page {url}: {str(e)}")
            if self.coverage_tracker:
                self.coverage_tracker.fail_page(url, str(e), retryable=True)
            return None

    async def _extract_components(self) -> List[WebComponent]:
        """Extract all components from current page."""
        components = []
        component_types = {
            "button": "button",
            "input": "input",
            "a": "link",
            "h1,h2,h3,h4,h5,h6": "heading",
            "p": "text",
            "img": "image",
            "table": "table",
            "form": "form",
        }
        
        for selector, comp_type in component_types.items():
            try:
                elements = await self.page.locator(selector).all()
                
                for i, element in enumerate(elements):
                    try:
                        # Get element properties
                        text = await element.text_content()
                        html = await element.inner_html()
                        
                        # Get bounding box for position
                        bbox = await element.bounding_box()
                        
                        # Get attributes
                        attrs = await self.page.evaluate(
                            "element => Object.fromEntries(Array.from(element.attributes).map(a => [a.name, a.value]))",
                            element
                        )
                        
                        # Create component object
                        component = WebComponent(
                            component_id=f"{comp_type}_{i}",
                            component_type=comp_type,
                            selector=f"{selector}:nth-of-type({i+1})",
                            actual_text=text or "",
                            actual_html=html or "",
                            attributes=attrs or {},
                            position=bbox if bbox else {}
                        )
                        
                        components.append(component)
                    
                    except Exception as e:
                        logger.debug(f"Failed to extract component: {str(e)}")
            
            except Exception as e:
                logger.debug(f"Failed to find {selector} elements: {str(e)}")
        
        return components

    async def _init_browser(self) -> None:
        """Initialize Playwright browser."""
        try:
            playwright = await async_playwright().start()
            
            # Select browser type
            if self.config.browser.type == "firefox":
                self.browser = await playwright.firefox.launch(headless=self.config.browser.headless)
            elif self.config.browser.type == "webkit":
                self.browser = await playwright.webkit.launch(headless=self.config.browser.headless)
            else:  # chromium (default)
                self.browser = await playwright.chromium.launch(headless=self.config.browser.headless)
            
            # Create context with viewport
            self.context = await self.browser.new_context(
                viewport={
                    "width": self.config.browser.viewport.width,
                    "height": self.config.browser.viewport.height
                },
                user_agent=self.config.browser.user_agent
            )
            
            self.page = await self.context.new_page()
            
            # Set timeouts
            self.page.set_default_navigation_timeout(self.config.browser.timeouts.navigation)
            
            # Handle authentication if needed
            await self._handle_auth()
            
            logger.info("Browser initialized successfully")
        
        except Exception as e:
            raise WebExtractionError(f"Failed to initialize browser: {str(e)}")

    async def _handle_auth(self) -> None:
        """Handle website authentication."""
        if self.config.website.authentication.type == "none":
            return
        
        try:
            auth_type = self.config.website.authentication.type
            
            if auth_type == "form":
                # Navigate to login URL
                login_url = self.config.website.login_url or self.config.website.url
                await self.page.goto(login_url)
                
                # Fill and submit form
                # This assumes standard form with id='username' and id='password'
                await self.page.fill('input[type="email"], input[name="email"], input[name="username"]', 
                                     self.config.website.username)
                await self.page.fill('input[type="password"]', 
                                     self.config.website.password)
                
                # Submit form
                await self.page.press('input[type="password"]', "Enter")
                
                # Wait for redirect
                await self.page.wait_for_load_state("networkidle")
                
                logger.info("Authentication successful")
            
            elif auth_type == "basic":
                # Basic auth is handled via context
                pass
            
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    async def _scroll_page(self) -> None:
        """Scroll page to load dynamic content."""
        scroll_behavior = self.config.website.extraction.scroll_behavior
        
        if scroll_behavior == "full":
            # Scroll to bottom
            await self.page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 100;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            
                            if(totalHeight >= scrollHeight){
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
        
        elif scroll_behavior == "lazy":
            # Scroll periodically to trigger lazy loading
            await self.page.evaluate("""
                () => {
                    window.scrollBy(0, window.innerHeight);
                }
            """)

    async def _take_screenshot(self, url: str) -> Optional[str]:
        """Take screenshot of page."""
        try:
            path = Path(self.config.browser.screenshots.directory)
            path.mkdir(parents=True, exist_ok=True)
            
            filename = f"screenshot_{len(self.visited_urls)}.png"
            filepath = path / filename
            
            await self.page.screenshot(
                path=str(filepath),
                full_page=self.config.browser.screenshots.full_page
            )
            
            return str(filepath)
        
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
            return None

    async def _get_links_from_page(self, page: Page) -> List[str]:
        """Get all links from current page."""
        try:
            links = await page.locator("a").all()
            urls = []
            
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if href and href.startswith("http"):
                        urls.append(href)
                except:
                    pass
            
            return urls
        except:
            return []

    async def _close_browser(self) -> None:
        """Close browser."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
```

### Step 2: Create Component Extractor Utility

**File:** `src/web_extraction/component_extractor.py`

```python
"""
Component extraction utilities for detecting and extracting web components.
"""

from typing import List, Dict, Any, Optional
from src.data.models import WebComponent, ComponentType


class ComponentExtractor:
    """Extract and classify web components."""
    
    @staticmethod
    def extract_from_html(html: str) -> List[WebComponent]:
        """Extract components from HTML."""
        # Placeholder for BeautifulSoup-based extraction
        components = []
        # Implementation would use BeautifulSoup or similar
        return components
    
    @staticmethod
    def classify_component(element: Any, selector: str) -> ComponentType:
        """Classify component type."""
        # Implementation would examine element and return type
        return ComponentType.OTHER
```

### Step 3: Create Auth Handler

**File:** `src/web_extraction/auth_handler.py`

```python
"""
Authentication handling for different auth types.
"""

from typing import Optional
from enum import Enum
from src.core.models import AuthType


class AuthHandler:
    """Handle website authentication."""
    
    async def authenticate(self, page, config) -> bool:
        """Authenticate based on auth type."""
        if config.website.authentication.type == AuthType.FORM:
            return await self._handle_form_auth(page, config)
        elif config.website.authentication.type == AuthType.BASIC:
            return await self._handle_basic_auth(page, config)
        return True
    
    async def _handle_form_auth(self, page, config) -> bool:
        """Handle form-based authentication."""
        # Implementation here
        pass
    
    async def _handle_basic_auth(self, page, config) -> bool:
        """Handle HTTP basic authentication."""
        # Implementation here
        pass
```

### Step 4: Update `__init__.py`

**File:** `src/web_extraction/__init__.py`

```python
"""
Web extraction module using Playwright.

Handles website navigation, authentication, component extraction,
and screenshot capture.
"""

from src.web_extraction.extractor import WebExtractor
from src.web_extraction.component_extractor import ComponentExtractor
from src.web_extraction.auth_handler import AuthHandler

__all__ = [
    "WebExtractor",
    "ComponentExtractor",
    "AuthHandler",
]
```

### Step 5: Integrate into Orchestrator

**File:** `src/agent/orchestrator.py` (update existing)

```python
# Add import
from src.web_extraction.extractor import WebExtractor

# In orchestrator.check_website() method, add:

async def check_website(self) -> Dict[str, Any]:
    """Extract and check entire website."""
    # Initialize web extractor
    extractor = WebExtractor(self.config, self.coverage_tracker)
    
    # Extract website
    extraction = await extractor.extract_website()
    
    # Store extraction data
    self.storage.save_extraction(extraction)
    
    # Process each page
    for page in extraction.pages:
        await self.check_page(page)
    
    return {
        "pages_checked": len(extraction.pages),
        "total_components": sum(len(p.components) for p in extraction.pages),
    }
```

### Step 6: Add Tests

**File:** `tests/unit/test_web_extractor.py`

```python
"""
Tests for web extractor.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.web_extraction.extractor import WebExtractor


@pytest.mark.asyncio
async def test_extract_page():
    """Test page extraction."""
    # Mock configuration
    config = MagicMock()
    config.website.url = "https://example.com"
    config.browser.viewport.width = 1280
    config.browser.viewport.height = 720
    
    # Mock Playwright
    with patch('src.web_extraction.extractor.async_playwright'):
        extractor = WebExtractor(config)
        
        # Test basic initialization
        assert extractor.config == config


@pytest.mark.asyncio
async def test_extract_components():
    """Test component extraction."""
    config = MagicMock()
    extractor = WebExtractor(config)
    
    # Mock page
    page = AsyncMock()
    extractor.page = page
    
    # Test component extraction
    components = await extractor._extract_components()
    
    assert isinstance(components, list)
```

---

## Installation & Setup

### 1. Add Playwright to requirements.txt

Already done (playwright==1.40.0)

### 2. Install Playwright browsers

```bash
playwright install chromium
# or for all browsers:
playwright install
```

### 3. Update imports in main.py

```python
from src.web_extraction.extractor import WebExtractor
```

---

## Testing the Implementation

### 1. Unit Tests

```bash
pytest tests/unit/test_web_extractor.py -v
```

### 2. Integration Test

```bash
# Test with example website
python main.py extract --config config/template_config.yaml
```

### 3. Full Pipeline Test

```bash
# Run complete pipeline
python main.py run --config config/waiverpo_config.yaml
```

---

## Common Issues & Solutions

### Issue: Playwright browser not launching

**Solution:**
```bash
playwright install chromium --with-deps
```

### Issue: Page navigation timeout

**Solution:** Increase timeout in config:
```yaml
browser:
  timeouts:
    page_load: 60000  # 60 seconds
```

### Issue: Authentication fails

**Solution:** Check selectors in your config:
```yaml
website:
  authentication:
    type: form
  extraction:
    wait_for_selectors:
      - "#dashboard"  # Element after login
```

---

## Validation Checklist

- [ ] Web extractor initializes correctly
- [ ] Browser launches with correct viewport
- [ ] Authentication succeeds (if configured)
- [ ] Pages are navigated successfully
- [ ] Components are extracted
- [ ] Screenshots are captured
- [ ] Data is stored in correct format
- [ ] Coverage tracking works
- [ ] Error handling works
- [ ] All tests pass
- [ ] Full pipeline works end-to-end

---

## Next Steps

Once web extraction is working:

1. Test with actual WaiverPro website
2. Capture sample screenshots
3. Generate sample reports
4. Update README with results
5. Push to GitHub

---

**Estimated Completion:** 4-6 hours  
**Required for:** End-to-end assignment completion
