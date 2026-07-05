"""
Configuration management system.

This module handles loading, parsing, validating, and managing all
configuration from YAML files and environment variables.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import lru_cache
import yaml
from dotenv import load_dotenv, dotenv_values

from src.core.exceptions import (
    ConfigurationError,
    InvalidConfigError,
    MissingConfigError,
)
from src.core.models import Config


class ConfigManager:
    """Manage application configuration from YAML and environment variables."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path or "config/base_config.yaml"
        self.config: Optional[Config] = None
        self.raw_config: Dict[str, Any] = {}
        self._env_vars: Dict[str, str] = {}

    def load(self) -> Config:
        """
        Load and validate configuration.

        Returns:
            Config object with all settings

        Raises:
            ConfigurationError: If loading fails
            InvalidConfigError: If validation fails
        """
        try:
            # Load environment variables
            self._load_env_vars()

            # Load YAML configuration
            raw_config = self._load_yaml()

            # Interpolate environment variables
            interpolated_config = self._interpolate_env_vars(raw_config)

            # Parse and validate with Pydantic
            self.config = Config.parse_obj(interpolated_config)

            return self.config

        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {str(e)}") from e

    def _load_env_vars(self) -> None:
        """Load environment variables from .env file and system environment."""
        # Load from .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)

        # Load all environment variables
        self._env_vars = dict(os.environ)

    def _load_yaml(self) -> Dict[str, Any]:
        """
        Load YAML configuration file.

        Returns:
            Dictionary with configuration

        Raises:
            FileNotFoundError: If config file not found
            yaml.YAMLError: If YAML parsing fails
        """
        config_path = Path(self.config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            if not config:
                raise InvalidConfigError(f"Configuration file is empty: {self.config_path}")

            # Handle config inheritance
            if "extends" in config:
                parent_config = self._load_parent_config(config.pop("extends"))
                config = self._merge_configs(parent_config, config)

            self.raw_config = config
            return config

        except yaml.YAMLError as e:
            raise InvalidConfigError(f"Invalid YAML in {self.config_path}: {str(e)}") from e

    def _load_parent_config(self, parent_path: str) -> Dict[str, Any]:
        """
        Load parent configuration file (for inheritance).

        Args:
            parent_path: Path to parent configuration

        Returns:
            Parent configuration dictionary
        """
        parent_full_path = Path(parent_path)
        if not parent_full_path.is_absolute():
            parent_full_path = Path("config") / parent_path

        if not parent_full_path.exists():
            raise FileNotFoundError(f"Parent configuration not found: {parent_path}")

        with open(parent_full_path, "r") as f:
            return yaml.safe_load(f)

    @staticmethod
    def _merge_configs(parent: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge child config into parent config (child overrides parent).

        Args:
            parent: Parent configuration
            child: Child configuration

        Returns:
            Merged configuration
        """
        merged = parent.copy()

        for key, value in child.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                merged[key] = ConfigManager._merge_configs(merged[key], value)
            else:
                # Override with child value
                merged[key] = value

        return merged

    def _interpolate_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interpolate environment variables in configuration.

        Supports:
        - ${VAR_NAME} - requires VAR_NAME to be set
        - ${VAR_NAME:default} - uses default if VAR_NAME not set

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with interpolated values

        Raises:
            MissingConfigError: If required env var not found
        """

        def interpolate_value(value: Any) -> Any:
            if isinstance(value, str):
                # Find all ${...} patterns
                pattern = r"\$\{([^}]+)\}"
                matches = re.findall(pattern, value)

                for match in matches:
                    if ":" in match:
                        # Has default: ${VAR:default}
                        var_name, default_value = match.split(":", 1)
                        env_value = self._env_vars.get(var_name.strip(), default_value.strip())
                    else:
                        # No default: ${VAR}
                        var_name = match.strip()
                        env_value = self._env_vars.get(var_name)
                        if env_value is None:
                            raise MissingConfigError(
                                f"Required environment variable not set: {var_name}"
                            )

                    # Replace placeholder with actual value
                    placeholder = "${" + match + "}"
                    value = value.replace(placeholder, env_value)

                return value

            elif isinstance(value, dict):
                # Recursively interpolate nested dictionaries
                return {k: interpolate_value(v) for k, v in value.items()}

            elif isinstance(value, list):
                # Recursively interpolate list items
                return [interpolate_value(item) for item in value]

            return value

        return interpolate_value(config)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., "website.url", "llm.model")
            default: Default value if key not found

        Returns:
            Configuration value

        Example:
            config_manager.get("website.url")
            config_manager.get("llm.temperature", default=0.7)
        """
        if not self.config:
            self.load()

        keys = key.split(".")
        value = self.config.dict()

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        try:
            if not self.config:
                self.load()

            # Configuration is valid if it loaded successfully
            return errors

        except Exception as e:
            errors.append(str(e))
            return errors

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration as dictionary
        """
        if not self.config:
            self.load()

        return self.config.dict()

    def to_yaml(self) -> str:
        """
        Convert configuration to YAML string.

        Returns:
            Configuration as YAML
        """
        if not self.config:
            self.load()

        return yaml.dump(self.config.dict(), default_flow_style=False, sort_keys=False)

    @staticmethod
    def create_from_env() -> Config:
        """
        Create configuration entirely from environment variables.

        This is useful for containerized deployments where YAML files
        are not available.

        Returns:
            Configuration object
        """
        manager = ConfigManager()
        manager._load_env_vars()

        # Create minimal YAML structure from env vars
        minimal_config = {
            "website": {
                "url": os.getenv("WEBSITE_URL", "https://example.com"),
            },
            "pdf": {
                "path": os.getenv("PDF_PATH", "./data/pdfs/guidelines.pdf"),
            },
        }

        # Interpolate and create config
        config = Config.parse_obj(minimal_config)
        return config


@lru_cache(maxsize=1)
def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get singleton configuration instance.

    Uses LRU cache to ensure same config object is returned.

    Args:
        config_path: Path to configuration file (cached on first call)

    Returns:
        Configuration object

    Example:
        config = get_config("config/waiverpo_config.yaml")
        llm_model = config.llm.model
    """
    manager = ConfigManager(config_path)
    return manager.load()


def load_config_from_file(config_path: str) -> Config:
    """
    Load configuration from file (no caching).

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration object
    """
    manager = ConfigManager(config_path)
    return manager.load()


def reset_config_cache() -> None:
    """Reset configuration cache (useful for testing)."""
    get_config.cache_clear()
