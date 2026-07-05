"""
Configuration and data validators.

Provides validation functions for common configuration values
and data structures.
"""

import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, List, Pattern


class URLValidator:
    """Validate URLs."""

    @staticmethod
    def is_valid(url: str) -> bool:
        """
        Check if URL is valid.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ["http", "https"], result.netloc])
        except Exception:
            return False

    @staticmethod
    def normalize(url: str) -> str:
        """
        Normalize URL (remove trailing slash).

        Args:
            url: URL to normalize

        Returns:
            Normalized URL
        """
        return url.rstrip("/")


class PathValidator:
    """Validate file paths."""

    @staticmethod
    def exists(path: str) -> bool:
        """
        Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if exists, False otherwise
        """
        try:
            return Path(path).exists()
        except Exception:
            return False

    @staticmethod
    def is_file(path: str) -> bool:
        """
        Check if path is a file.

        Args:
            path: Path to check

        Returns:
            True if is file, False otherwise
        """
        try:
            return Path(path).is_file()
        except Exception:
            return False

    @staticmethod
    def is_dir(path: str) -> bool:
        """
        Check if path is a directory.

        Args:
            path: Path to check

        Returns:
            True if is directory, False otherwise
        """
        try:
            return Path(path).is_dir()
        except Exception:
            return False

    @staticmethod
    def is_readable(path: str) -> bool:
        """
        Check if path is readable.

        Args:
            path: Path to check

        Returns:
            True if readable, False otherwise
        """
        try:
            return Path(path).exists() and os.access(path, os.R_OK)
        except Exception:
            return False


class RegexValidator:
    """Validate regex patterns."""

    @staticmethod
    def is_valid_pattern(pattern: str) -> bool:
        """
        Check if string is valid regex.

        Args:
            pattern: Pattern to validate

        Returns:
            True if valid regex, False otherwise
        """
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False

    @staticmethod
    def compile(pattern: str) -> Optional[Pattern]:
        """
        Compile regex pattern.

        Args:
            pattern: Pattern to compile

        Returns:
            Compiled pattern or None if invalid
        """
        try:
            return re.compile(pattern)
        except re.error:
            return None


class CredentialsValidator:
    """Validate credentials."""

    @staticmethod
    def is_valid_api_key(key: str) -> bool:
        """
        Check if API key format is valid.

        Args:
            key: API key to validate

        Returns:
            True if looks like valid key, False otherwise
        """
        if not key or len(key) < 10:
            return False
        # Check if it looks like an API key (alphanumeric + special chars)
        return bool(re.match(r"^[a-zA-Z0-9\-_.]+$", key))

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        Check if email is valid.

        Args:
            email: Email to validate

        Returns:
            True if valid email format, False otherwise
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_username(username: str) -> bool:
        """
        Check if username is valid.

        Args:
            username: Username to validate

        Returns:
            True if valid format, False otherwise
        """
        if not username or len(username) < 3:
            return False
        # Alphanumeric, underscore, hyphen
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", username))


class SelectorValidator:
    """Validate CSS selectors."""

    @staticmethod
    def is_valid_css_selector(selector: str) -> bool:
        """
        Check if string looks like valid CSS selector.

        Args:
            selector: Selector to validate

        Returns:
            True if looks valid, False otherwise
        """
        if not selector or len(selector) < 1:
            return False

        # Very basic validation - just check it doesn't have obvious issues
        invalid_chars = ["<", ">", "{", "}", ";", "\\"]
        return not any(char in selector for char in invalid_chars)


class PortValidator:
    """Validate port numbers."""

    @staticmethod
    def is_valid_port(port: int) -> bool:
        """
        Check if port is valid.

        Args:
            port: Port number to validate

        Returns:
            True if valid port (1-65535), False otherwise
        """
        return 1 <= port <= 65535

    @staticmethod
    def is_privileged(port: int) -> bool:
        """
        Check if port is privileged.

        Args:
            port: Port number to check

        Returns:
            True if port < 1024, False otherwise
        """
        return port < 1024


class RangeValidator:
    """Validate numeric ranges."""

    @staticmethod
    def is_in_range(value: float, min_val: float = None, max_val: float = None) -> bool:
        """
        Check if value is within range.

        Args:
            value: Value to check
            min_val: Minimum (inclusive), None for no minimum
            max_val: Maximum (inclusive), None for no maximum

        Returns:
            True if in range, False otherwise
        """
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True

    @staticmethod
    def is_percentage(value: float) -> bool:
        """
        Check if value is valid percentage (0-100).

        Args:
            value: Value to check

        Returns:
            True if valid percentage, False otherwise
        """
        return 0 <= value <= 100


class ConfigValidator:
    """Validate complete configuration objects."""

    @staticmethod
    def validate_website_url(url: str) -> bool:
        """Validate website URL."""
        return URLValidator.is_valid(url)

    @staticmethod
    def validate_pdf_path(path: str) -> bool:
        """Validate PDF file path."""
        if not PathValidator.is_file(path):
            return False
        return path.lower().endswith(".pdf")

    @staticmethod
    def validate_output_dir(path: str) -> bool:
        """Validate output directory (must be writable)."""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_api_key(key: Optional[str], required: bool = False) -> bool:
        """Validate API key."""
        if not key:
            return not required
        return CredentialsValidator.is_valid_api_key(key)

    @staticmethod
    def validate_port(port: int) -> bool:
        """Validate port number."""
        return PortValidator.is_valid_port(port)

    @staticmethod
    def validate_temperature(temp: float) -> bool:
        """Validate LLM temperature (0-1)."""
        return RangeValidator.is_in_range(temp, 0.0, 1.0)

    @staticmethod
    def validate_confidence_threshold(threshold: float) -> bool:
        """Validate confidence threshold (0-1)."""
        return RangeValidator.is_in_range(threshold, 0.0, 1.0)

    @staticmethod
    def validate_coverage_percentage(percentage: float) -> bool:
        """Validate coverage percentage (0-100)."""
        return RangeValidator.is_percentage(percentage)


# Import at module level
import os
