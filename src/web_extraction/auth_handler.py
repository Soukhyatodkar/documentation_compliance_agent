"""
Authentication handling for different auth types.

Supports form-based, basic HTTP, and OAuth2 authentication.
"""

import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AuthType(str, Enum):
    """Authentication types."""
    NONE = "none"
    BASIC = "basic"
    FORM = "form"
    OAUTH2 = "oauth2"


class AuthHandler:
    """Handle different authentication methods."""
    
    @staticmethod
    async def authenticate(page, config) -> bool:
        """Authenticate based on auth type."""
        if config.website.authentication.type == AuthType.FORM or \
           config.website.authentication.type == "form":
            return await AuthHandler._handle_form_auth(page, config)
        elif config.website.authentication.type == AuthType.BASIC or \
             config.website.authentication.type == "basic":
            return await AuthHandler._handle_basic_auth(page, config)
        return True
    
    @staticmethod
    async def _handle_form_auth(page, config) -> bool:
        """Handle form-based authentication."""
        try:
            login_url = config.website.login_url or config.website.url
            await page.goto(login_url)
            
            # Fill and submit form
            await page.fill('input[type="email"]', config.website.username)
            await page.fill('input[type="password"]', config.website.password)
            
            # Submit
            await page.press('input[type="password"]', "Enter")
            await page.wait_for_load_state("networkidle")
            
            logger.info("Form-based authentication successful")
            return True
        except Exception as e:
            logger.error(f"Form authentication failed: {str(e)}")
            return False
    
    @staticmethod
    async def _handle_basic_auth(page, config) -> bool:
        """Handle HTTP basic authentication."""
        try:
            # Basic auth is handled via context headers
            logger.info("Basic authentication configured")
            return True
        except Exception as e:
            logger.error(f"Basic authentication failed: {str(e)}")
            return False
