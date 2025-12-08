"""Error handling and retry logic for trading operations."""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union

from fastapi import HTTPException, status


logger = logging.getLogger(__name__)

T = TypeVar("T")


class TradeErrorType(str, Enum):
    """Types of trading errors."""
    NETWORK_ERROR = "network_error"
    BROKER_ERROR = "broker_error"
    INSUFFICIENT_MARGIN = "insufficient_margin"
    INVALID_SYMBOL = "invalid_symbol"
    INVALID_VOLUME = "invalid_volume"
    MARKET_CLOSED = "market_closed"
    PRICE_CHANGED = "price_changed"
    ORDER_REJECTED = "order_rejected"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class TradeError(Exception):
    """Custom exception for trading errors."""

    def __init__(
        self,
        error_type: TradeErrorType,
        message: str,
        retryable: bool = False,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.retryable = retryable
        self.details = details or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


def classify_error(error: Exception) -> TradeError:
    """Classify an exception into a TradeError."""
    error_str = str(error).lower()

    if "timeout" in error_str or "timed out" in error_str:
        return TradeError(
            TradeErrorType.TIMEOUT,
            "Operation timed out",
            retryable=True,
        )
    elif "connection" in error_str or "network" in error_str:
        return TradeError(
            TradeErrorType.NETWORK_ERROR,
            "Network connection error",
            retryable=True,
        )
    elif "margin" in error_str or "money" in error_str:
        return TradeError(
            TradeErrorType.INSUFFICIENT_MARGIN,
            "Insufficient margin for this trade",
            retryable=False,
        )
    elif "symbol" in error_str or "not found" in error_str:
        return TradeError(
            TradeErrorType.INVALID_SYMBOL,
            "Invalid trading symbol",
            retryable=False,
        )
    elif "volume" in error_str or "lot" in error_str:
        return TradeError(
            TradeErrorType.INVALID_VOLUME,
            "Invalid volume/lot size",
            retryable=False,
        )
    elif "market" in error_str and "closed" in error_str:
        return TradeError(
            TradeErrorType.MARKET_CLOSED,
            "Market is closed",
            retryable=False,
        )
    elif "price" in error_str:
        return TradeError(
            TradeErrorType.PRICE_CHANGED,
            "Price has changed, please retry",
            retryable=True,
        )
    elif "reject" in error_str:
        return TradeError(
            TradeErrorType.ORDER_REJECTED,
            "Order was rejected by broker",
            retryable=False,
            details={"original_error": str(error)},
        )
    else:
        return TradeError(
            TradeErrorType.UNKNOWN,
            f"Unknown error: {str(error)}",
            retryable=False,
            details={"original_error": str(error)},
        )


def retry_on_failure(
    max_retries: int = 3,
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_errors: Optional[list[TradeErrorType]] = None,
):
    """
    Decorator for retrying failed operations.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay_seconds: Initial delay between retries
        backoff_factor: Multiplier for delay on each retry
        retryable_errors: List of error types to retry (None = all retryable)
    """
    if retryable_errors is None:
        retryable_errors = [
            TradeErrorType.NETWORK_ERROR,
            TradeErrorType.TIMEOUT,
            TradeErrorType.PRICE_CHANGED,
        ]

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_error = None
            delay = delay_seconds

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except TradeError as e:
                    last_error = e
                    if e.error_type in retryable_errors and attempt < max_retries:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e.message}"
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise
                except Exception as e:
                    trade_error = classify_error(e)
                    if trade_error.retryable and attempt < max_retries:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {trade_error.message}"
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                        last_error = trade_error
                    else:
                        raise trade_error

            raise last_error

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_error = None
            delay = delay_seconds

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except TradeError as e:
                    last_error = e
                    if e.error_type in retryable_errors and attempt < max_retries:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e.message}"
                        )
                        import time
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise
                except Exception as e:
                    trade_error = classify_error(e)
                    if trade_error.retryable and attempt < max_retries:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {trade_error.message}"
                        )
                        import time
                        time.sleep(delay)
                        delay *= backoff_factor
                        last_error = trade_error
                    else:
                        raise trade_error

            raise last_error

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for protecting against cascading failures.
    
    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Failing, requests are blocked
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._failure_count = 0
        self._success_count = 0
        self._state = "closed"
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> str:
        if self._state == "open":
            import time
            if time.time() - (self._last_failure_time or 0) > self.recovery_timeout:
                self._state = "half_open"
                self._success_count = 0
        return self._state

    def can_execute(self) -> bool:
        """Check if operation can proceed."""
        return self.state != "open"

    def record_success(self):
        """Record successful operation."""
        if self._state == "half_open":
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = "closed"
                self._failure_count = 0
        else:
            self._failure_count = 0

    def record_failure(self):
        """Record failed operation."""
        import time
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning("Circuit breaker opened due to failures")

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Use as decorator."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            if not self.can_execute():
                raise TradeError(
                    TradeErrorType.BROKER_ERROR,
                    "Service temporarily unavailable (circuit breaker open)",
                    retryable=True,
                )

            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            if not self.can_execute():
                raise TradeError(
                    TradeErrorType.BROKER_ERROR,
                    "Service temporarily unavailable (circuit breaker open)",
                    retryable=True,
                )

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


# Global circuit breakers for different services
mt5_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
api_circuit_breaker = CircuitBreaker(failure_threshold=10, recovery_timeout=30)
