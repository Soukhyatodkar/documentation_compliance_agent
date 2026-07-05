"""
Unit tests for validators module.
"""

import pytest
from src.utils.validators import (
    URLValidator,
    CredentialsValidator,
    ConfigValidator,
    PortValidator,
    RangeValidator,
    RegexValidator,
)


class TestURLValidator:
    """Tests for URLValidator."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert URLValidator.is_valid("https://example.com") is True

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert URLValidator.is_valid("http://example.com") is True

    def test_invalid_url_no_scheme(self):
        """Test invalid URL without scheme."""
        assert URLValidator.is_valid("example.com") is False

    def test_invalid_url_no_domain(self):
        """Test invalid URL without domain."""
        assert URLValidator.is_valid("https://") is False

    def test_normalize_url(self):
        """Test URL normalization."""
        assert URLValidator.normalize("https://example.com/") == "https://example.com"
        assert URLValidator.normalize("https://example.com") == "https://example.com"


class TestCredentialsValidator:
    """Tests for CredentialsValidator."""

    def test_valid_api_key(self):
        """Test valid API key."""
        assert CredentialsValidator.is_valid_api_key("sk-1234567890abcdef") is True

    def test_invalid_api_key_too_short(self):
        """Test invalid API key (too short)."""
        assert CredentialsValidator.is_valid_api_key("sk-123") is False

    def test_invalid_api_key_empty(self):
        """Test invalid API key (empty)."""
        assert CredentialsValidator.is_valid_api_key("") is False

    def test_valid_email(self):
        """Test valid email."""
        assert CredentialsValidator.is_valid_email("user@example.com") is True

    def test_invalid_email_no_domain(self):
        """Test invalid email without domain."""
        assert CredentialsValidator.is_valid_email("user@") is False

    def test_invalid_email_no_tld(self):
        """Test invalid email without TLD."""
        assert CredentialsValidator.is_valid_email("user@example") is False

    def test_valid_username(self):
        """Test valid username."""
        assert CredentialsValidator.is_valid_username("valid_user-123") is True

    def test_invalid_username_too_short(self):
        """Test invalid username (too short)."""
        assert CredentialsValidator.is_valid_username("ab") is False

    def test_invalid_username_special_chars(self):
        """Test invalid username with special characters."""
        assert CredentialsValidator.is_valid_username("user@name") is False


class TestPortValidator:
    """Tests for PortValidator."""

    def test_valid_port(self):
        """Test valid port."""
        assert PortValidator.is_valid_port(8080) is True
        assert PortValidator.is_valid_port(1) is True
        assert PortValidator.is_valid_port(65535) is True

    def test_invalid_port_too_low(self):
        """Test invalid port (too low)."""
        assert PortValidator.is_valid_port(0) is False

    def test_invalid_port_too_high(self):
        """Test invalid port (too high)."""
        assert PortValidator.is_valid_port(65536) is False

    def test_is_privileged_port(self):
        """Test checking if port is privileged."""
        assert PortValidator.is_privileged(80) is True
        assert PortValidator.is_privileged(443) is True
        assert PortValidator.is_privileged(1024) is False


class TestRangeValidator:
    """Tests for RangeValidator."""

    def test_in_range(self):
        """Test value in range."""
        assert RangeValidator.is_in_range(5, min_val=0, max_val=10) is True

    def test_below_min(self):
        """Test value below minimum."""
        assert RangeValidator.is_in_range(-1, min_val=0, max_val=10) is False

    def test_above_max(self):
        """Test value above maximum."""
        assert RangeValidator.is_in_range(11, min_val=0, max_val=10) is False

    def test_is_percentage(self):
        """Test percentage validation."""
        assert RangeValidator.is_percentage(50) is True
        assert RangeValidator.is_percentage(0) is True
        assert RangeValidator.is_percentage(100) is True

    def test_invalid_percentage_negative(self):
        """Test invalid percentage (negative)."""
        assert RangeValidator.is_percentage(-1) is False

    def test_invalid_percentage_over_100(self):
        """Test invalid percentage (over 100)."""
        assert RangeValidator.is_percentage(101) is False


class TestRegexValidator:
    """Tests for RegexValidator."""

    def test_valid_regex(self):
        """Test valid regex pattern."""
        assert RegexValidator.is_valid_pattern(r"^[a-z]+$") is True

    def test_invalid_regex(self):
        """Test invalid regex pattern."""
        assert RegexValidator.is_valid_pattern(r"[a-z") is False

    def test_compile_regex(self):
        """Test compiling regex."""
        pattern = RegexValidator.compile(r"^test$")
        assert pattern is not None
        assert pattern.match("test") is not None


class TestConfigValidator:
    """Tests for ConfigValidator."""

    def test_validate_api_key_required(self):
        """Test API key validation (required)."""
        assert ConfigValidator.validate_api_key("sk-valid-key", required=True) is True
        assert ConfigValidator.validate_api_key(None, required=True) is False

    def test_validate_api_key_optional(self):
        """Test API key validation (optional)."""
        assert ConfigValidator.validate_api_key(None, required=False) is True

    def test_validate_port(self):
        """Test port validation."""
        assert ConfigValidator.validate_port(8000) is True
        assert ConfigValidator.validate_port(70000) is False

    def test_validate_temperature(self):
        """Test temperature validation."""
        assert ConfigValidator.validate_temperature(0.7) is True
        assert ConfigValidator.validate_temperature(1.5) is False

    def test_validate_confidence_threshold(self):
        """Test confidence threshold validation."""
        assert ConfigValidator.validate_confidence_threshold(0.8) is True
        assert ConfigValidator.validate_confidence_threshold(1.5) is False

    def test_validate_coverage_percentage(self):
        """Test coverage percentage validation."""
        assert ConfigValidator.validate_coverage_percentage(80.0) is True
        assert ConfigValidator.validate_coverage_percentage(101.0) is False
