"""
Retry mechanisms for resilient operations.

Implements exponential backoff with jitter for robust failure handling.
"""

import asyncio
import time
import random
from typing import Callable, TypeVar, Any, Optional, Type
from functools import wraps
import logging

from src.core.exceptions import RetryError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_ms: int = 1000,
        backoff_multiplier: float = 2.0,
        max_delay_ms: int = 30000,
        exponential: bool = True,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retries
            initial_delay_ms: Initial delay in milliseconds
            backoff_multiplier: Multiplier for exponential backoff
            max_delay_ms: Maximum delay in milliseconds
            exponential: Use exponential backoff
            jitter: Add random jitter to delays
        """
        self.max_retries = max_retries
        self.initial_delay_ms = initial_delay_ms
        self.backoff_multiplier = backoff_multiplier
        self.max_delay_ms = max_delay_ms
        self.exponential = exponential
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if self.exponential:
            delay_ms = min(
                self.initial_delay_ms * (self.backoff_multiplier ** attempt),
                self.max_delay_ms,
            )
        else:
            delay_ms = self.initial_delay_ms

        # Add jitter
        if self.jitter:
            jitter_ms = random.uniform(0, delay_ms * 0.1)
            delay_ms += jitter_ms

        return delay_ms / 1000.0  # Convert to seconds


def retry(
    max_retries: int = 3,
    initial_delay_ms: int = 1000,
    backoff_multiplier: float = 2.0,
    max_delay_ms: int = 30000,
    exponential: bool = True,
    jitter: bool = True,
    exceptions: Optional[tuple] = None,
) -> Callable:
    """
    Retry decorator for synchronous functions.

    Args:
        max_retries: Maximum number of retries
        initial_delay_ms: Initial delay in milliseconds
        backoff_multiplier: Multiplier for exponential backoff
        max_delay_ms: Maximum delay in milliseconds
        exponential: Use exponential backoff
        jitter: Add random jitter to delays
        exceptions: Tuple of exceptions to catch (default: Exception)

    Returns:
        Decorated function

    Example:
        @retry(max_retries=3, exceptions=(ConnectionError, TimeoutError))
        def fetch_data():
            return requests.get("https://api.example.com/data")
    """
    if exceptions is None:
        exceptions = (Exception,)

    config = RetryConfig(
        max_retries=max_retries,
        initial_delay_ms=initial_delay_ms,
        backoff_multiplier=backoff_multiplier,
        max_delay_ms=max_delay_ms,
        exponential=exponential,
        jitter=jitter,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {str(e)}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_retries + 1} attempts failed for {func.__name__}"
                        )

            raise RetryError(f"Max retries ({config.max_retries}) exceeded") from last_exception

        return wrapper

    return decorator


def async_retry(
    max_retries: int = 3,
    initial_delay_ms: int = 1000,
    backoff_multiplier: float = 2.0,
    max_delay_ms: int = 30000,
    exponential: bool = True,
    jitter: bool = True,
    exceptions: Optional[tuple] = None,
) -> Callable:
    """
    Retry decorator for async functions.

    Args:
        max_retries: Maximum number of retries
        initial_delay_ms: Initial delay in milliseconds
        backoff_multiplier: Multiplier for exponential backoff
        max_delay_ms: Maximum delay in milliseconds
        exponential: Use exponential backoff
        jitter: Add random jitter to delays
        exceptions: Tuple of exceptions to catch (default: Exception)

    Returns:
        Decorated async function

    Example:
        @async_retry(max_retries=3, exceptions=(ConnectionError,))
        async def fetch_data():
            return await aiohttp_client.get("https://api.example.com/data")
    """
    if exceptions is None:
        exceptions = (Exception,)

    config = RetryConfig(
        max_retries=max_retries,
        initial_delay_ms=initial_delay_ms,
        backoff_multiplier=backoff_multiplier,
        max_delay_ms=max_delay_ms,
        exponential=exponential,
        jitter=jitter,
    )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {str(e)}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_retries + 1} attempts failed for {func.__name__}"
                        )

            raise RetryError(f"Max retries ({config.max_retries}) exceeded") from last_exception

        return wrapper

    return decorator


class RetryableOperation:
    """Manually retryable operation."""

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retryable operation.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        self.attempt = 0

    def should_retry(self, exception: Exception) -> bool:
        """
        Check if should retry.

        Args:
            exception: Exception that occurred

        Returns:
            True if should retry, False otherwise
        """
        return self.attempt < self.config.max_retries

    def wait(self) -> None:
        """Wait before next retry."""
        delay = self.config.get_delay(self.attempt)
        logger.debug(f"Waiting {delay:.1f}s before retry (attempt {self.attempt + 1})")
        time.sleep(delay)
        self.attempt += 1

    async def wait_async(self) -> None:
        """Wait before next retry (async)."""
        delay = self.config.get_delay(self.attempt)
        logger.debug(f"Waiting {delay:.1f}s before retry (attempt {self.attempt + 1})")
        await asyncio.sleep(delay)
        self.attempt += 1


def retry_on_exception(
    exceptions: tuple = (Exception,),
    max_retries: int = 3,
) -> Callable:
    """
    Simplified retry decorator that only retries on specific exceptions.

    Args:
        exceptions: Tuple of exception types to retry on
        max_retries: Maximum number of retries

    Returns:
        Decorated function

    Example:
        @retry_on_exception(exceptions=(TimeoutError,), max_retries=3)
        def risky_operation():
            return dangerous_api_call()
    """
    return retry(
        max_retries=max_retries,
        exceptions=exceptions,
        exponential=True,
        jitter=True,
    )
