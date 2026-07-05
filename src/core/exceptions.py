"""
Custom exceptions for the Documentation Compliance Agent.

This module defines all custom exceptions used throughout the application
for proper error handling and debugging.
"""


class ComplianceAgentError(Exception):
    """Base exception for all Compliance Agent errors."""

    pass


class ConfigurationError(ComplianceAgentError):
    """Raised when configuration loading or validation fails."""

    pass


class InvalidConfigError(ConfigurationError):
    """Raised when configuration values are invalid."""

    pass


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing."""

    pass


class EnvironmentError(ComplianceAgentError):
    """Raised when environment setup fails."""

    pass


class PDFProcessingError(ComplianceAgentError):
    """Raised when PDF processing fails."""

    pass


class WebExtractionError(ComplianceAgentError):
    """Raised when web extraction fails."""

    pass


class VectorDatabaseError(ComplianceAgentError):
    """Raised when vector database operations fail."""

    pass


class EmbeddingError(ComplianceAgentError):
    """Raised when embedding generation fails."""

    pass


class LLMError(ComplianceAgentError):
    """Raised when LLM operations fail."""

    pass


class RAGError(ComplianceAgentError):
    """Raised when RAG pipeline fails."""

    pass


class AuthenticationError(ComplianceAgentError):
    """Raised when authentication fails."""

    pass


class ReportGenerationError(ComplianceAgentError):
    """Raised when report generation fails."""

    pass


class ValidationError(ComplianceAgentError):
    """Raised when data validation fails."""

    pass


class RetryError(ComplianceAgentError):
    """Raised when maximum retries exceeded."""

    pass


class TimeoutError(ComplianceAgentError):  # noqa: A001
    """Raised when operation times out."""

    pass


class ConnectionError(ComplianceAgentError):  # noqa: A001
    """Raised when connection fails."""

    pass


class ExternalAPIError(ComplianceAgentError):
    """Raised when external API calls fail."""

    pass


class ProcessingError(ComplianceAgentError):
    """Raised when general processing fails."""

    pass


class StorageError(ComplianceAgentError):
    """Raised when data storage operations fail."""

    pass
