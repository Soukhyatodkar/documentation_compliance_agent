"""
Structured logging setup for the application.

Provides consistent, structured logging across all modules with
support for JSON, simple, and structured formats.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import json
import structlog

from src.core.models import Config, LogFormat, LogLevel


class JSONFormatter(logging.Formatter):
    """JSON formatter for logging records."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


class StructuredFormatter(logging.Formatter):
    """Structured formatter using structlog."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Build structured message
        msg_dict = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
        }

        # Parse message if it looks like key=value format
        message = record.getMessage()
        if "=" in message:
            try:
                pairs = message.split("|")
                for pair in pairs:
                    key, value = pair.split("=", 1)
                    msg_dict[key.strip()] = value.strip()
            except ValueError:
                msg_dict["message"] = message
        else:
            msg_dict["message"] = message

        # Add exception info
        if record.exc_info:
            msg_dict["exception"] = self.formatException(record.exc_info)

        return json.dumps(msg_dict, default=str)


class LoggerSetup:
    """Configure application logging."""

    def __init__(self, config: Config):
        """
        Initialize logger setup.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger("compliance_agent")

    def setup(self) -> logging.Logger:
        """
        Set up logging based on configuration.

        Returns:
            Configured logger instance
        """
        # Clear existing handlers
        self.logger.handlers.clear()

        # Set log level
        log_level = getattr(logging, self.config.logging.level.value)
        self.logger.setLevel(log_level)

        # Ensure log directory exists
        log_file_path = Path(self.config.logging.file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create formatter based on format setting
        if self.config.logging.format == LogFormat.JSON:
            formatter = JSONFormatter()
        elif self.config.logging.format == LogFormat.STRUCTURED:
            formatter = StructuredFormatter()
        else:
            # Simple format
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        # File handler with rotation
        if self.config.logging.rotation.enabled:
            file_handler = logging.handlers.RotatingFileHandler(
                self.config.logging.file,
                maxBytes=self.config.logging.rotation.max_size_mb * 1024 * 1024,
                backupCount=self.config.logging.rotation.backup_count,
            )
        else:
            file_handler = logging.FileHandler(self.config.logging.file)

        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler (DEBUG and above always goes to console in debug mode)
        if self.config.app.debug:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        return self.logger

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get logger for a specific module.

        Args:
            name: Module name

        Returns:
            Configured logger instance
        """
        return logging.getLogger(f"compliance_agent.{name}")


def setup_logging(config: Config) -> logging.Logger:
    """
    Setup application logging (convenience function).

    Args:
        config: Application configuration

    Returns:
        Configured logger instance

    Example:
        logger = setup_logging(config)
        logger.info("Starting application")
    """
    setup = LoggerSetup(config)
    return setup.setup()


def get_logger(name: str) -> logging.Logger:
    """
    Get logger for a module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance

    Example:
        logger = get_logger(__name__)
        logger.debug("Debug message")
    """
    return logging.getLogger(f"compliance_agent.{name}")


class StructuredLogger:
    """Wrapper for structured logging with contextual information."""

    def __init__(self, logger: logging.Logger):
        """
        Initialize structured logger.

        Args:
            logger: Underlying logger instance
        """
        self.logger = logger

    def info(self, message: str, **kwargs) -> None:
        """Log info message with structured data."""
        if kwargs:
            message = self._build_message(message, **kwargs)
        self.logger.info(message)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with structured data."""
        if kwargs:
            message = self._build_message(message, **kwargs)
        self.logger.debug(message)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with structured data."""
        if kwargs:
            message = self._build_message(message, **kwargs)
        self.logger.warning(message)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with structured data."""
        if kwargs:
            message = self._build_message(message, **kwargs)
        self.logger.error(message)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with structured data."""
        if kwargs:
            message = self._build_message(message, **kwargs)
        self.logger.critical(message)

    @staticmethod
    def _build_message(message: str, **kwargs) -> str:
        """Build structured message."""
        pairs = [f"{k}={v}" for k, v in kwargs.items()]
        if pairs:
            return f"{message} | {' | '.join(pairs)}"
        return message


# ============================================================================
# Context managers for logging
# ============================================================================


class LogContext:
    """Context manager for logging operation progress."""

    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        """
        Initialize log context.

        Args:
            logger: Logger instance
            operation: Operation name
            **kwargs: Additional context data
        """
        self.logger = logger
        self.operation = operation
        self.context = kwargs

    def __enter__(self):
        """Enter context."""
        self.logger.info(f"Starting {self.operation}", extra={"operation": self.operation})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type is None:
            self.logger.info(f"Completed {self.operation}")
        else:
            self.logger.error(
                f"Failed {self.operation}: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb),
            )
        return False
