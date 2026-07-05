"""
Unit tests for configuration system.
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from src.core.config import ConfigManager, get_config, load_config_from_file, reset_config_cache
from src.core.exceptions import ConfigurationError, InvalidConfigError, MissingConfigError
from src.core.models import Config


class TestConfigManager:
    """Tests for ConfigManager class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "website": {
                    "url": "https://example.com",
                    "authentication": {"type": "none"},
                },
                "pdf": {
                    "path": "./data/pdfs/test.pdf",
                },
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink()

    def test_load_valid_config(self, temp_config_file):
        """Test loading valid configuration."""
        manager = ConfigManager(temp_config_file)
        config = manager.load()

        assert config is not None
        assert config.website.url == "https://example.com"
        assert config.pdf.path == "./data/pdfs/test.pdf"

    def test_load_missing_file(self):
        """Test loading non-existent config file."""
        manager = ConfigManager("/nonexistent/config.yaml")

        with pytest.raises(ConfigurationError):
            manager.load()

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            with pytest.raises(ConfigurationError):
                manager.load()
        finally:
            Path(temp_path).unlink()

    def test_get_config_value_by_key(self, temp_config_file):
        """Test getting config value by dot-notation key."""
        manager = ConfigManager(temp_config_file)
        manager.load()

        assert manager.get("website.url") == "https://example.com"
        assert manager.get("pdf.path") == "./data/pdfs/test.pdf"

    def test_get_config_with_default(self, temp_config_file):
        """Test getting config with default value."""
        manager = ConfigManager(temp_config_file)
        manager.load()

        result = manager.get("nonexistent.key", default="default_value")
        assert result == "default_value"

    def test_environment_variable_interpolation(self):
        """Test environment variable interpolation."""
        import os

        os.environ["TEST_URL"] = "https://test.example.com"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "website": {
                    "url": "${TEST_URL}",
                    "authentication": {"type": "none"},
                },
                "pdf": {
                    "path": "./data/pdfs/test.pdf",
                },
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            config = manager.load()
            assert config.website.url == "https://test.example.com"
        finally:
            Path(temp_path).unlink()
            del os.environ["TEST_URL"]

    def test_environment_variable_with_default(self):
        """Test environment variable interpolation with default."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "website": {
                    "url": "${NONEXISTENT_VAR:https://default.com}",
                    "authentication": {"type": "none"},
                },
                "pdf": {
                    "path": "./data/pdfs/test.pdf",
                },
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            config = manager.load()
            assert config.website.url == "https://default.com"
        finally:
            Path(temp_path).unlink()

    def test_missing_required_env_var(self):
        """Test error when required env var is missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "website": {
                    "url": "${REQUIRED_URL}",
                    "authentication": {"type": "none"},
                },
                "pdf": {
                    "path": "./data/pdfs/test.pdf",
                },
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            with pytest.raises(ConfigurationError):
                manager.load()
        finally:
            Path(temp_path).unlink()

    def test_validate_returns_empty_list_when_valid(self, temp_config_file):
        """Test validate returns empty list when config is valid."""
        manager = ConfigManager(temp_config_file)
        manager.load()

        errors = manager.validate()
        assert errors == []

    def test_to_dict(self, temp_config_file):
        """Test converting config to dictionary."""
        manager = ConfigManager(temp_config_file)
        manager.load()

        config_dict = manager.to_dict()
        assert isinstance(config_dict, dict)
        assert "website" in config_dict
        assert "pdf" in config_dict

    def test_to_yaml(self, temp_config_file):
        """Test converting config to YAML string."""
        manager = ConfigManager(temp_config_file)
        manager.load()

        yaml_str = manager.to_yaml()
        assert isinstance(yaml_str, str)
        assert "website:" in yaml_str or "pdf:" in yaml_str


class TestConfigValidation:
    """Tests for configuration validation."""

    @pytest.fixture
    def valid_config(self):
        """Create valid config for testing."""
        return {
            "website": {
                "url": "https://example.com",
                "authentication": {"type": "none"},
            },
            "pdf": {
                "path": "./data/pdfs/test.pdf",
            },
        }

    def test_invalid_temperature(self, valid_config):
        """Test validation of invalid LLM temperature."""
        valid_config["llm"] = {"temperature": 1.5}  # Invalid: > 1.0

        with pytest.raises(Exception):  # Pydantic validation error
            Config.parse_obj(valid_config)

    def test_invalid_port(self, valid_config):
        """Test validation of invalid port number."""
        valid_config["advanced"] = {"monitoring_port": 70000}  # Invalid: > 65535

        with pytest.raises(Exception):  # Pydantic validation error
            Config.parse_obj(valid_config)

    def test_invalid_retry_delays(self, valid_config):
        """Test validation of retry delay configuration."""
        valid_config["retry"] = {
            "initial_delay_ms": 5000,
            "max_delay_ms": 1000,  # Invalid: max < initial
        }

        with pytest.raises(Exception):  # Pydantic validation error
            Config.parse_obj(valid_config)


class TestConfigCaching:
    """Tests for config caching."""

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "website": {
                    "url": "https://example.com",
                    "authentication": {"type": "none"},
                },
                "pdf": {
                    "path": "./data/pdfs/test.pdf",
                },
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink()

    def test_get_config_returns_same_instance(self, temp_config_file):
        """Test that get_config returns same instance (cached)."""
        reset_config_cache()

        config1 = get_config(temp_config_file)
        config2 = get_config(temp_config_file)

        assert config1 is config2

    def test_load_config_from_file_without_caching(self, temp_config_file):
        """Test load_config_from_file does not use caching."""
        config1 = load_config_from_file(temp_config_file)
        config2 = load_config_from_file(temp_config_file)

        # Different instances (not cached)
        assert config1 is not config2
