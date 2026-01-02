"""Circuit breaker pattern for WLED command reliability."""
from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, TypeVar

from .const import CIRCUIT_BREAKER_FAILURE_THRESHOLD, CIRCUIT_BREAKER_TIMEOUT
from .errors import CircuitBreakerOpenError

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Prevent repeated failures from overwhelming the system.
    
    This implements the circuit breaker pattern to protect against
    cascading failures when communicating with WLED devices.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are blocked
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(
        self,
        failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        timeout: float = CIRCUIT_BREAKER_TIMEOUT,
        name: str = "default",
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
            name: Name for logging purposes
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._success_count = 0
        self._lock = asyncio.Lock()

        _LOGGER.debug(
            "Circuit breaker '%s' initialized: threshold=%d, timeout=%.1fs",
            name,
            failure_threshold,
            timeout,
        )

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception raised by func
        """
        async with self._lock:
            # Check if we should attempt recovery
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    _LOGGER.info(
                        "Circuit breaker '%s' entering HALF_OPEN state",
                        self.name,
                    )
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN"
                    )

        # Execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result

        except Exception as err:
            await self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset.

        Returns:
            True if should attempt reset
        """
        if self._last_failure_time is None:
            return False

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.timeout

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self._success_count += 1

            if self._state == CircuitState.HALF_OPEN:
                _LOGGER.info(
                    "Circuit breaker '%s' recovered, entering CLOSED state",
                    self.name,
                )
                self._state = CircuitState.CLOSED
                self._failure_count = 0

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                _LOGGER.warning(
                    "Circuit breaker '%s' failed during HALF_OPEN, returning to OPEN",
                    self.name,
                )
                self._state = CircuitState.OPEN

            elif self._failure_count >= self.failure_threshold:
                _LOGGER.error(
                    "Circuit breaker '%s' threshold reached (%d failures), entering OPEN state",
                    self.name,
                    self._failure_count,
                )
                self._state = CircuitState.OPEN

    @property
    def state(self) -> CircuitState:
        """Get current state."""
        return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self._state == CircuitState.CLOSED

    @property
    def failure_count(self) -> int:
        """Get failure count."""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """Get success count."""
        return self._success_count

    async def reset(self) -> None:
        """Manually reset the circuit breaker."""
        async with self._lock:
            _LOGGER.info("Manually resetting circuit breaker '%s'", self.name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics.

        Returns:
            Dict with statistics
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout,
        }
