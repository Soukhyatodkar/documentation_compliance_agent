"""
Main website extraction orchestrator using Playwright.

Handles authentication, page navigation, component extraction,
and screenshot capture for automated compliance checking.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Set
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import structlog

from src.core.models import Config
from src.core.exceptions import WebExtractionError, AuthenticationError
from src.data.models import WebComponent, WebPage, WebsiteExtraction, ComponentType
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
        self.base_url = config.website.url
        self.domain = urlparse(self.base_url).netloc
        
        logger.info(f"Initialized WebExtractor for {self.base_url}", 
                    extraction_id=self.extraction_id)

    async def extract_website(self) -> WebsiteExtraction:
        """Extract entire website using crawling strategy."""
        start_time = datetime.now()
        pages = []
        urls_to_visit = [self.config.website.url]
        max_pages = self.config.website.crawling.max_pages
        max_links = self.config.website.crawling.max_links
        
        try:
            await self._init_browser()
            logger.info("Browser initialized, starting crawl")
            
            links_found = 0
            
            while urls_to_visit and len(pages) < max_pages:
                url = urls_to_visit.pop(0)
                
                # Skip already visited
                if url in self.visited_urls:
                    continue
                
                # Skip excluded patterns
                if self._should_skip_url(url):
                    logger.debug(f"Skipping URL (filtered): {url}")
                    continue
                
                try:
                    logger.info(f"Extracting page {len(pages) + 1}/{max_pages}: {url}")
                    page_data = await self.extract_page(url)
                    
                    if page_data:
                        pages.append(page_data)
                        
                        # Extract new URLs for crawling
                        if links_found < max_links:
                            new_urls = await self._get_links_from_page()
                            for new_url in new_urls:
                                if (new_url not in self.visited_urls and 
                                    links_found < max_links and
                                    self._is_same_domain(new_url)):
                                    urls_to_visit.append(new_url)
                                    links_found += 1
                
                except Exception as e:
                    logger.error(f"Failed to extract {url}", error=str(e))
                    if self.coverage_tracker:
                        self.coverage_tracker.fail_page(url, str(e), retryable=True)
            
            # Create extraction result
            duration = (datetime.now() - start_time).total_seconds()
            extraction = WebsiteExtraction(
                extraction_id=self.extraction_id,
                website_url=self.config.website.url,
                pages=pages,
                total_pages_extracted=len(pages),
                total_pages_attempted=len(self.visited_urls),
                started_at=start_time.isoformat(),
                completed_at=datetime.now().isoformat(),
                metadata={
                    "duration_seconds": duration,
                    "extraction_method": "playwright_crawl",
                    "browser_type": self.config.browser.type,
                    "headless": self.config.browser.headless,
                }
            )
            
            logger.info(
                "Website extraction complete",
                pages=len(pages),
                duration=duration,
                avg_components=sum(len(p.components) for p in pages) / len(pages) if pages else 0
            )
            
            return extraction
            
        finally:
            await self._close_browser()

    async def extract_page(self, url: str) -> Optional[WebPage]:
        """Extract single page with components and screenshots."""
        try:
            # Navigate to page
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            self.visited_urls.add(url)
            
            if self.coverage_tracker:
                self.coverage_tracker.start_page(url, f"page_{len(self.visited_urls)}")
            
            logger.debug(f"Page loaded: {url}")
            
            # Wait for dynamic content if configured
            if self.config.website.extraction.wait_for_selectors:
                for selector in self.config.website.extraction.wait_for_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        logger.debug(f"Found selector: {selector}")
                    except Exception:
                        logger.debug(f"Selector not found: {selector}")
            
            # Execute custom JavaScript if configured
            if self.config.website.extraction.execute_js:
                try:
                    await self.page.evaluate(self.config.website.extraction.execute_js)
                    logger.debug("Custom JavaScript executed")
                except Exception as e:
                    logger.warning(f"Failed to execute custom JS: {str(e)}")
            
            # Handle scrolling for lazy-loaded content
            if self.config.website.extraction.scroll_behavior != "none":
                await self._scroll_page()
            
            # Extract page metadata
            title = await self.page.title()
            description = None
            try:
                description = await self.page.locator('meta[name="description"]').get_attribute("content")
            except:
                pass
            
            # Extract all text content
            page_text = ""
            try:
                page_text = await self.page.locator("body").text_content() or ""
            except:
                pass
            
            # Extract components
            components = await self._extract_components()
            logger.info(f"Extracted {len(components)} components from {url}")
            
            # Take screenshot
            screenshot_path = None
            if self.config.browser.screenshots.enabled:
                screenshot_path = await self._take_screenshot(url)
            
            # Create page object
            page_data = WebPage(
                page_id=f"page_{len(self.visited_urls)}",
                url=url,
                title=title or "Untitled",
                description=description,
                page_text=page_text,
                components=components,
                screenshot_path=screenshot_path,
                extracted_at=datetime.now().isoformat(),
                extraction_duration_seconds=0.0,
            )
            
            if self.coverage_tracker:
                self.coverage_tracker.succeed_page(
                    url,
                    components_count=len(components),
                    text_length=len(page_text),
                    title=title,
                    http_status=200,
                    screenshot_taken=screenshot_path is not None
                )
            
            return page_data
            
        except Exception as e:
            logger.error(f"Failed to extract page {url}", error=str(e))
            if self.coverage_tracker:
                self.coverage_tracker.fail_page(url, str(e), retryable=True)
            return None

    async def _extract_components(self) -> List[WebComponent]:
        """Extract all components from current page."""
        components: List[WebComponent] = []
        component_id_counter = 0
        
        # Define selectors for different component types
        selectors_map = {
            "button": ["button", "input[type='button']", "input[type='submit']", "[role='button']"],
            "link": ["a"],
            "input": ["input[type='text']", "input[type='email']", "input[type='password']", 
                     "textarea", "select"],
            "heading": ["h1", "h2", "h3", "h4", "h5", "h6"],
            "text": ["p", "span", "div[role='main'] > *"],
            "form": ["form"],
            "table": ["table"],
            "image": ["img"],
            "navigation": ["nav", "header"],
        }
        
        try:
            for comp_type, selectors in selectors_map.items():
                for selector in selectors:
                    try:
                        elements = await self.page.locator(selector).all()
                        
                        for idx, element in enumerate(elements):
                            try:
                                # Skip hidden elements
                                is_visible = await element.is_visible()
                                if not is_visible:
                                    continue
                                
                                # Get element properties
                                text = await element.text_content() or ""
                                text = text.strip()[:200]  # Limit text length
                                
                                if not text:
                                    continue
                                
                                html = await element.inner_html() or ""
                                html = html[:500]  # Limit HTML length
                                
                                # Get bounding box for position
                                bbox = await element.bounding_box()
                                
                                # Get attributes
                                try:
                                    attrs = await self.page.evaluate(
                                        "element => Object.fromEntries(Array.from(element.attributes).map(a => [a.name, a.value]))",
                                        element
                                    )
                                except:
                                    attrs = {}
                                
                                # Create component object
                                component = WebComponent(
                                    component_id=f"{comp_type}_{component_id_counter}",
                                    component_type=comp_type,
                                    selector=selector,
                                    actual_text=text,
                                    actual_html=html[:200],
                                    attributes=attrs or {},
                                    position={
                                        "x": int(bbox["x"]) if bbox else 0,
                                        "y": int(bbox["y"]) if bbox else 0,
                                        "width": int(bbox["width"]) if bbox else 0,
                                        "height": int(bbox["height"]) if bbox else 0,
                                    }
                                )
                                
                                components.append(component)
                                component_id_counter += 1
                            
                            except Exception as e:
                                logger.debug(f"Failed to extract component: {str(e)}")
                    
                    except Exception as e:
                        logger.debug(f"Failed to find {selector} elements: {str(e)}")
        
        except Exception as e:
            logger.error(f"Component extraction failed: {str(e)}")
        
        return components

    async def _init_browser(self) -> None:
        """Initialize Playwright browser and authenticate."""
        try:
            playwright = await async_playwright().start()
            
            # Select browser type
            if self.config.browser.type == "firefox":
                self.browser = await playwright.firefox.launch(
                    headless=self.config.browser.headless
                )
            elif self.config.browser.type == "webkit":
                self.browser = await playwright.webkit.launch(
                    headless=self.config.browser.headless
                )
            else:  # chromium (default)
                self.browser = await playwright.chromium.launch(
                    headless=self.config.browser.headless
                )
            
            logger.info(f"Browser launched: {self.config.browser.type}")
            
            # Create context with viewport
            self.context = await self.browser.new_context(
                viewport={
                    "width": self.config.browser.viewport.width,
                    "height": self.config.browser.viewport.height
                },
                user_agent=self.config.browser.user_agent or None,
                ignore_https_errors=True,
            )
            
            self.page = await self.context.new_page()
            
            # Set timeouts
            self.page.set_default_navigation_timeout(self.config.browser.timeouts.navigation)
            self.page.set_default_timeout(self.config.browser.timeouts.element_wait)
            
            logger.info("Browser context created")
            
            # Handle authentication if needed
            if self.config.website.authentication.type != "none":
                await self._handle_auth()
            
            logger.info("Browser initialization complete")
        
        except Exception as e:
            raise WebExtractionError(f"Failed to initialize browser: {str(e)}")

    async def _handle_auth(self) -> None:
        """Handle website authentication (form-based)."""
        if self.config.website.authentication.type == "none":
            return
        
        try:
            auth_type = self.config.website.authentication.type
            logger.info(f"Starting authentication: {auth_type}")
            
            if auth_type == "form":
                # Navigate to login URL
                login_url = self.config.website.login_url or self.config.website.url
                logger.info(f"Navigating to login URL: {login_url}")
                
                await self.page.goto(login_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(1)  # Wait for page to render
                
                # Find and fill email field - try multiple selectors
                email_selectors = [
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[placeholder*="mail" i]',
                    'input[placeholder*="Email" i]',
                    '#email',
                    'input[autocomplete="email"]'
                ]
                
                email_filled = False
                for selector in email_selectors:
                    try:
                        await self.page.fill(selector, self.config.website.username, timeout=3000)
                        logger.info(f"Filled email with selector: {selector}")
                        email_filled = True
                        break
                    except Exception:
                        continue
                
                if not email_filled:
                    raise AuthenticationError("Could not find email input field")
                
                # Find and fill password field - try multiple selectors
                password_selectors = [
                    'input[type="password"]',
                    'input[name="password"]',
                    'input[placeholder*="assword" i]',
                    'input[placeholder*="Password" i]',
                    '#password',
                    'input[autocomplete="current-password"]'
                ]
                
                password_filled = False
                for selector in password_selectors:
                    try:
                        await self.page.fill(selector, self.config.website.password, timeout=3000)
                        logger.info(f"Filled password with selector: {selector}")
                        password_filled = True
                        break
                    except Exception:
                        continue
                
                if not password_filled:
                    raise AuthenticationError("Could not find password input field")
                
                # Submit form - try multiple methods
                submit_success = False
                
                # Method 1: Find submit button
                submit_buttons = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign In")',
                    'button:has-text("Submit")',
                ]
                
                for selector in submit_buttons:
                    try:
                        await self.page.click(selector, timeout=5000)
                        logger.info(f"Clicked submit button: {selector}")
                        submit_success = True
                        break
                    except Exception:
                        continue
                
                # Method 2: Press Enter on password field
                if not submit_success:
                    try:
                        await self.page.press('input[type="password"]', "Enter", timeout=5000)
                        logger.info("Submitted form by pressing Enter")
                        submit_success = True
                    except Exception:
                        pass
                
                # Wait for navigation to complete
                try:
                    await self.page.wait_for_url("**", wait_until="networkidle", timeout=30000)
                    logger.info("Authentication successful - page loaded")
                except Exception:
                    logger.warning("Timeout waiting for post-login page")
                
                await asyncio.sleep(2)  # Extra wait for page stability
            
            else:
                logger.warning(f"Authentication type {auth_type} not yet supported")
        
        except AuthenticationError as e:
            raise e
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    async def _scroll_page(self) -> None:
        """Scroll page to load dynamic/lazy-loaded content."""
        try:
            scroll_behavior = self.config.website.extraction.scroll_behavior
            
            if scroll_behavior == "full":
                logger.debug("Scrolling to bottom of page")
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
                logger.debug("Page scroll complete")
            
            elif scroll_behavior == "lazy":
                logger.debug("Scrolling to trigger lazy loading")
                await self.page.evaluate("""
                    () => {
                        window.scrollBy(0, window.innerHeight);
                    }
                """)
        
        except Exception as e:
            logger.warning(f"Scroll operation failed: {str(e)}")

    async def _take_screenshot(self, url: str) -> Optional[str]:
        """Take screenshot of current page."""
        try:
            path = Path(self.config.browser.screenshots.directory)
            path.mkdir(parents=True, exist_ok=True)
            
            # Create unique filename
            page_index = len(self.visited_urls)
            filename = f"screenshot_{page_index:03d}.png"
            filepath = path / filename
            
            await self.page.screenshot(
                path=str(filepath),
                full_page=self.config.browser.screenshots.full_page
            )
            
            logger.debug(f"Screenshot saved: {filepath}")
            return str(filepath)
        
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
            return None

    async def _get_links_from_page(self) -> List[str]:
        """Get all internal links from current page."""
        try:
            links = await self.page.locator("a[href]").all()
            urls = []
            
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if href:
                        # Convert relative URLs to absolute
                        absolute_url = urljoin(self.base_url, href)
                        
                        # Only include same-domain links
                        if self._is_same_domain(absolute_url) and absolute_url not in self.visited_urls:
                            urls.append(absolute_url)
                except Exception:
                    pass
            
            return urls
        
        except Exception as e:
            logger.debug(f"Failed to extract links: {str(e)}")
            return []

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL is on same domain."""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain
        except:
            return False

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped based on configuration."""
        skip_patterns = self.config.website.crawling.skip_urls or []
        
        for pattern in skip_patterns:
            if pattern.lower() in url.lower():
                return True
        
        return False

    async def _close_browser(self) -> None:
        """Close browser and clean up resources."""
        try:
            if self.context:
                await self.context.close()
                logger.debug("Context closed")
            if self.browser:
                await self.browser.close()
                logger.debug("Browser closed")
            logger.info("Browser resources cleaned up")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
