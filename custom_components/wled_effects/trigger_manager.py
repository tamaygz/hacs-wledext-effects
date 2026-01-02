"""Trigger management for context-aware effects."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from homeassistant.core import Event, HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class TriggerConfig:
    """Configuration for a trigger."""

    trigger_type: str  # state_change, threshold, time, event
    entity_id: str | None = None
    attribute: str | None = None
    threshold: float | None = None
    comparison: str = ">"  # >, <, ==, >=, <=
    time_pattern: str | None = None  # HH:MM format
    event_type: str | None = None
    event_data: dict[str, Any] | None = None


class TriggerManager:
    """Manage triggers for context-aware effects.
    
    Monitors Home Assistant state changes, events, and time patterns
    to trigger effect behavior changes.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize trigger manager.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass
        self._triggers: dict[str, TriggerConfig] = {}
        self._callbacks: dict[str, list[Callable]] = {}
        self._listeners: list[Callable] = []
        self._time_task: asyncio.Task | None = None

    def add_trigger(
        self,
        trigger_id: str,
        trigger_config: TriggerConfig,
        callback: Callable,
    ) -> None:
        """Add a trigger with callback.

        Args:
            trigger_id: Unique identifier for trigger
            trigger_config: Trigger configuration
            callback: Async callback function when trigger fires
        """
        self._triggers[trigger_id] = trigger_config

        if trigger_id not in self._callbacks:
            self._callbacks[trigger_id] = []
        self._callbacks[trigger_id].append(callback)

        _LOGGER.debug("Added trigger %s: %s", trigger_id, trigger_config)

    async def setup(self) -> None:
        """Setup trigger listeners."""
        for trigger_id, config in self._triggers.items():
            if config.trigger_type == "state_change":
                await self._setup_state_trigger(trigger_id, config)
            elif config.trigger_type == "threshold":
                await self._setup_threshold_trigger(trigger_id, config)
            elif config.trigger_type == "time":
                await self._setup_time_trigger(trigger_id, config)
            elif config.trigger_type == "event":
                await self._setup_event_trigger(trigger_id, config)

    async def _setup_state_trigger(
        self,
        trigger_id: str,
        config: TriggerConfig,
    ) -> None:
        """Setup state change trigger."""
        if not config.entity_id:
            _LOGGER.warning("State trigger %s missing entity_id", trigger_id)
            return

        async def state_changed(event: Event) -> None:
            """Handle state change event."""
            new_state = event.data.get("new_state")
            if not new_state:
                return

            # Get value
            if config.attribute:
                value = new_state.attributes.get(config.attribute)
            else:
                value = new_state.state

            # Fire callbacks
            await self._fire_trigger(trigger_id, {"value": value, "state": new_state})

        # Subscribe to state changes
        self._listeners.append(
            self.hass.bus.async_listen(
                f"state_changed_{config.entity_id}",
                state_changed,
            )
        )

    async def _setup_threshold_trigger(
        self,
        trigger_id: str,
        config: TriggerConfig,
    ) -> None:
        """Setup threshold trigger."""
        if not config.entity_id or config.threshold is None:
            _LOGGER.warning("Threshold trigger %s missing entity_id or threshold", trigger_id)
            return

        last_triggered = False

        async def state_changed(event: Event) -> None:
            """Handle state change for threshold check."""
            nonlocal last_triggered

            new_state = event.data.get("new_state")
            if not new_state:
                return

            # Get numeric value
            if config.attribute:
                value_str = new_state.attributes.get(config.attribute)
            else:
                value_str = new_state.state

            try:
                value = float(value_str)
            except (ValueError, TypeError):
                return

            # Check threshold
            triggered = False
            if config.comparison == ">":
                triggered = value > config.threshold
            elif config.comparison == "<":
                triggered = value < config.threshold
            elif config.comparison == "==":
                triggered = value == config.threshold
            elif config.comparison == ">=":
                triggered = value >= config.threshold
            elif config.comparison == "<=":
                triggered = value <= config.threshold

            # Fire only on transition
            if triggered and not last_triggered:
                await self._fire_trigger(
                    trigger_id,
                    {"value": value, "threshold": config.threshold},
                )

            last_triggered = triggered

        self._listeners.append(
            self.hass.bus.async_listen(
                f"state_changed_{config.entity_id}",
                state_changed,
            )
        )

    async def _setup_time_trigger(
        self,
        trigger_id: str,
        config: TriggerConfig,
    ) -> None:
        """Setup time-based trigger."""
        if not config.time_pattern:
            _LOGGER.warning("Time trigger %s missing time_pattern", trigger_id)
            return

        try:
            hour, minute = map(int, config.time_pattern.split(":"))
            trigger_time = time(hour, minute)
        except (ValueError, AttributeError):
            _LOGGER.error("Invalid time pattern: %s", config.time_pattern)
            return

        async def check_time() -> None:
            """Check if current time matches trigger."""
            while True:
                now = datetime.now().time()
                if now.hour == trigger_time.hour and now.minute == trigger_time.minute:
                    await self._fire_trigger(trigger_id, {"time": now})
                    # Wait until next minute to avoid duplicate triggers
                    await asyncio.sleep(60)
                else:
                    # Check every 30 seconds
                    await asyncio.sleep(30)

        if not self._time_task or self._time_task.done():
            self._time_task = self.hass.async_create_task(check_time())

    async def _setup_event_trigger(
        self,
        trigger_id: str,
        config: TriggerConfig,
    ) -> None:
        """Setup event-based trigger."""
        if not config.event_type:
            _LOGGER.warning("Event trigger %s missing event_type", trigger_id)
            return

        async def event_fired(event: Event) -> None:
            """Handle event."""
            # Check event data match if specified
            if config.event_data:
                for key, value in config.event_data.items():
                    if event.data.get(key) != value:
                        return

            await self._fire_trigger(trigger_id, {"event": event})

        self._listeners.append(
            self.hass.bus.async_listen(config.event_type, event_fired)
        )

    async def _fire_trigger(self, trigger_id: str, data: dict[str, Any]) -> None:
        """Fire trigger callbacks.

        Args:
            trigger_id: Trigger identifier
            data: Data to pass to callbacks
        """
        _LOGGER.debug("Trigger fired: %s with data: %s", trigger_id, data)

        callbacks = self._callbacks.get(trigger_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as err:
                _LOGGER.error("Error in trigger callback: %s", err)

    async def shutdown(self) -> None:
        """Cleanup trigger listeners."""
        for listener in self._listeners:
            listener()
        self._listeners.clear()

        if self._time_task and not self._time_task.done():
            self._time_task.cancel()
            try:
                await self._time_task
            except asyncio.CancelledError:
                pass
