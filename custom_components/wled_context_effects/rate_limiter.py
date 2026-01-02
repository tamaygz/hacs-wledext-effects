"""Rate limiter for WLED commands."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque

from .const import MAX_COMMANDS_PER_SECOND, RATE_LIMIT_WINDOW
from .errors import RateLimitError

_LOGGER = logging.getLogger(__name__)


class RateLimiter:
    """Limit WLED command rate to prevent device overload.
    
    This class implements a sliding window rate limiter to ensure
    we don't send too many commands to WLED devices in a short time.
    """

    def __init__(
        self,
        max_commands: int = MAX_COMMANDS_PER_SECOND,
        window: float = RATE_LIMIT_WINDOW,
    ) -> None:
        """Initialize rate limiter.

        Args:
            max_commands: Maximum commands allowed per window
            window: Time window in seconds
        """
        self.max_commands = max_commands
        self.window = window
        self._timestamps: deque[float] = deque(maxlen=max_commands)
        self._lock = asyncio.Lock()
        _LOGGER.debug(
            "Rate limiter initialized: %d commands per %.1fs",
            max_commands,
            window,
        )

    async def acquire(self, timeout: float | None = None) -> None:
        """Acquire permission to send command.

        This method will wait if necessary to maintain the rate limit.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Raises:
            RateLimitError: If timeout is reached
            asyncio.TimeoutError: If timeout is reached
        """
        async with self._lock:
            start_time = time.time()

            while True:
                current_time = time.time()

                # Remove old timestamps outside the window
                while self._timestamps and self._timestamps[0] < current_time - self.window:
                    self._timestamps.popleft()

                # Check if we can proceed
                if len(self._timestamps) < self.max_commands:
                    self._timestamps.append(current_time)
                    _LOGGER.debug(
                        "Rate limit check passed (%d/%d commands in window)",
                        len(self._timestamps),
                        self.max_commands,
                    )
                    return

                # Calculate wait time
                if self._timestamps:
                    oldest = self._timestamps[0]
                    wait_time = (oldest + self.window) - current_time
                else:
                    wait_time = 0.1  # Small default wait

                # Check timeout
                if timeout is not None:
                    elapsed = current_time - start_time
                    if elapsed >= timeout:
                        _LOGGER.warning("Rate limit timeout reached")
                        raise RateLimitError(
                            f"Rate limit timeout ({timeout}s) reached"
                        )
                    wait_time = min(wait_time, timeout - elapsed)

                _LOGGER.debug(
                    "Rate limit reached, waiting %.2fs (%d/%d commands)",
                    wait_time,
                    len(self._timestamps),
                    self.max_commands,
                )
                await asyncio.sleep(wait_time)

    def can_proceed(self) -> bool:
        """Check if a command can proceed without waiting.

        Returns:
            True if under rate limit
        """
        current_time = time.time()

        # Remove old timestamps
        while self._timestamps and self._timestamps[0] < current_time - self.window:
            self._timestamps.popleft()

        return len(self._timestamps) < self.max_commands

    @property
    def current_rate(self) -> int:
        """Get current number of commands in the window.

        Returns:
            Number of commands in current window
        """
        current_time = time.time()

        # Remove old timestamps
        while self._timestamps and self._timestamps[0] < current_time - self.window:
            self._timestamps.popleft()

        return len(self._timestamps)

    @property
    def available_slots(self) -> int:
        """Get number of available command slots.

        Returns:
            Number of commands that can be sent immediately
        """
        return max(0, self.max_commands - self.current_rate)

    def reset(self) -> None:
        """Reset the rate limiter."""
        _LOGGER.debug("Resetting rate limiter")
        self._timestamps.clear()
