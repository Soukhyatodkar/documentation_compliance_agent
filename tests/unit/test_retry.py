"""
Unit tests for retry module.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.utils.retry import (
    RetryConfig,
    retry,
    async_retry,
    RetryableOperation,
    retry_on_exception,
)
from src.core.exceptions import RetryError


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_exponential_delay(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            max_retries=3,
            initial_delay_ms=1000,
            backoff_multiplier=2.0,
            max_delay_ms=30000,
            exponential=True,
            jitter=False,
        )

        # Delays should double each time
        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            max_retries=10,
            initial_delay_ms=1000,
            backoff_multiplier=2.0,
            max_delay_ms=5000,
            exponential=True,
            jitter=False,
        )

        # Should cap at 5000ms (5 seconds)
        assert config.get_delay(10) == 5.0

    def test_linear_delay(self):
        """Test linear delay (non-exponential)."""
        config = RetryConfig(
            max_retries=3,
            initial_delay_ms=1000,
            exponential=False,
            jitter=False,
        )

        # All delays should be the same
        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 1.0
        assert config.get_delay(2) == 1.0


class TestRetryDecorator:
    """Tests for retry decorator."""

    def test_retry_success_first_attempt(self):
        """Test successful operation on first attempt."""

        @retry(max_retries=3, exponential=False)
        def successful_func():
            return "success"

        result = successful_func()
        assert result == "success"

    def test_retry_after_failures(self):
        """Test retry after failures."""
        call_count = 0

        @retry(max_retries=3, initial_delay_ms=10, exponential=False)
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Failed")
            return "success"

        result = failing_then_success()
        assert result == "success"
        assert call_count == 3

    def test_retry_max_retries_exceeded(self):
        """Test error when max retries exceeded."""

        @retry(max_retries=2, initial_delay_ms=10, exponential=False)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(RetryError):
            always_fails()

    def test_retry_specific_exception(self):
        """Test retry only on specific exceptions."""

        @retry(
            max_retries=2,
            initial_delay_ms=10,
            exceptions=(ValueError,),
            exponential=False,
        )
        def raises_other_error():
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            raises_other_error()


class TestAsyncRetryDecorator:
    """Tests for async retry decorator."""

    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        """Test successful async operation."""

        @async_retry(max_retries=3)
        async def successful_async_func():
            return "success"

        result = await successful_async_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_retry_after_failures(self):
        """Test async retry after failures."""
        call_count = 0

        @async_retry(max_retries=3, initial_delay_ms=10, exponential=False)
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Failed")
            return "success"

        result = await failing_then_success()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_max_retries_exceeded(self):
        """Test error when max async retries exceeded."""

        @async_retry(max_retries=1, initial_delay_ms=10, exponential=False)
        async def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(RetryError):
            await always_fails()


class TestRetryableOperation:
    """Tests for RetryableOperation class."""

    def test_should_retry(self):
        """Test should_retry method."""
        operation = RetryableOperation(RetryConfig(max_retries=3))

        assert operation.should_retry(ValueError("test")) is True
        operation.attempt += 1
        assert operation.should_retry(ValueError("test")) is True
        operation.attempt += 1
        assert operation.should_retry(ValueError("test")) is True
        operation.attempt += 1
        assert operation.should_retry(ValueError("test")) is False

    def test_wait(self):
        """Test wait method."""
        config = RetryConfig(
            max_retries=3,
            initial_delay_ms=10,
            exponential=False,
            jitter=False,
        )
        operation = RetryableOperation(config)

        with patch("time.sleep") as mock_sleep:
            operation.wait()
            mock_sleep.assert_called_once_with(0.01)

    @pytest.mark.asyncio
    async def test_wait_async(self):
        """Test async wait method."""
        config = RetryConfig(
            max_retries=3,
            initial_delay_ms=10,
            exponential=False,
            jitter=False,
        )
        operation = RetryableOperation(config)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await operation.wait_async()
            mock_sleep.assert_called_once()


class TestRetryOnException:
    """Tests for retry_on_exception decorator."""

    def test_retry_on_specific_exception(self):
        """Test retrying only on specific exception."""
        call_count = 0

        @retry_on_exception(exceptions=(ConnectionError,), max_retries=2)
        def connection_fails():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Failed")
            return "success"

        result = connection_fails()
        assert result == "success"

    def test_no_retry_on_other_exception(self):
        """Test not retrying on other exceptions."""

        @retry_on_exception(exceptions=(ConnectionError,), max_retries=2)
        def different_error():
            raise ValueError("Different error")

        with pytest.raises(ValueError):
            different_error()
