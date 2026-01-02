"""Coordinators for WLED Effects integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_COMMAND_COUNT,
    ATTR_FAILURE_COUNT,
    ATTR_LAST_ERROR,
    ATTR_SUCCESS_COUNT,
    ATTR_SUCCESS_RATE,
    DEFAULT_STATE_SOURCE_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    STATE_ERROR,
    STATE_RUNNING,
    STATE_STOPPED,
)
from .errors import EffectExecutionError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .effects.base import WLEDEffectBase

_LOGGER = logging.getLogger(__name__)


class EffectCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate effect state and execution.
    
    This coordinator manages the lifecycle of an effect and provides
    state information to all associated entities.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        effect: WLEDEffectBase,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            effect: Effect instance to coordinate
            entry: Config entry
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"WLED Effect {effect.get_effect_name()}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.effect = effect
        self.entry = entry
        self._last_started: datetime | None = None
        self._last_stopped: datetime | None = None

        _LOGGER.debug(
            "Effect coordinator initialized for %s",
            effect.get_effect_name(),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from effect.

        Returns:
            Dict with effect state data
        """
        try:
            return {
                "running": self.effect.running,
                "effect_type": self.effect.get_effect_name(),
                "last_updated": datetime.now(),
                "last_error": self.effect.last_error,
                "statistics": {
                    ATTR_COMMAND_COUNT: self.effect.command_count,
                    ATTR_SUCCESS_COUNT: self.effect.success_count,
                    ATTR_FAILURE_COUNT: self.effect.failure_count,
                    ATTR_SUCCESS_RATE: self.effect.success_rate,
                    ATTR_LAST_ERROR: self.effect.last_error,
                },
                "state": self._get_state(),
                "last_started": self._last_started,
                "last_stopped": self._last_stopped,
                "running_time": self.effect.running_time,
            }
        except Exception as err:
            _LOGGER.error("Error updating effect coordinator: %s", err)
            raise UpdateFailed(f"Error updating effect data: {err}") from err

    def _get_state(self) -> str:
        """Get current state string."""
        if self.effect.last_error:
            return STATE_ERROR
        if self.effect.running:
            return STATE_RUNNING
        return STATE_STOPPED

    async def async_start_effect(self) -> None:
        """Start the effect."""
        try:
            _LOGGER.info("Starting effect %s", self.effect.get_effect_name())
            await self.effect.start()
            self._last_started = datetime.now()
            await self.async_request_refresh()

        except Exception as err:
            _LOGGER.error("Failed to start effect: %s", err)
            raise EffectExecutionError(f"Failed to start effect: {err}") from err

    async def async_stop_effect(self) -> None:
        """Stop the effect."""
        try:
            _LOGGER.info("Stopping effect %s", self.effect.get_effect_name())
            await self.effect.stop()
            self._last_stopped = datetime.now()
            await self.async_request_refresh()

        except Exception as err:
            _LOGGER.error("Failed to stop effect: %s", err)
            raise EffectExecutionError(f"Failed to stop effect: {err}") from err

    async def async_run_once(self) -> None:
        """Run effect once."""
        try:
            _LOGGER.info("Running effect %s once", self.effect.get_effect_name())
            await self.effect.run_once()
            await self.async_request_refresh()

        except Exception as err:
            _LOGGER.error("Failed to run effect once: %s", err)
            raise EffectExecutionError(f"Failed to run effect once: {err}") from err

    async def async_update_config(self, config: dict[str, Any]) -> None:
        """Update effect configuration.

        Args:
            config: New configuration values
        """
        _LOGGER.info("Updating effect configuration: %s", config)
        
        # Validate numeric values
        if "brightness" in config:
            brightness = config["brightness"]
            if not isinstance(brightness, int) or not 0 <= brightness <= 255:
                raise ValueError(f"Invalid brightness value: {brightness}")
        
        if "segment_id" in config:
            segment_id = config["segment_id"]
            if not isinstance(segment_id, int) or not 0 <= segment_id <= 31:
                raise ValueError(f"Invalid segment_id: {segment_id}")
        
        # Update config dict
        self.effect.config.update(config)
        
        # Apply common config updates
        if "brightness" in config:
            self.effect.brightness = config["brightness"]
        if "segment_id" in config:
            self.effect.segment_id = config["segment_id"]
        if "start_led" in config:
            self.effect.start_led = config["start_led"]
        if "stop_led" in config:
            self.effect.stop_led = config["stop_led"]
        
        await self.async_request_refresh()


class StateSourceCoordinator(DataUpdateCoordinator[Any]):
    """Track state changes from Home Assistant entities.
    
    This coordinator monitors a source entity and provides its state/attribute
    value to reactive effects.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        attribute: str | None = None,
        update_interval: timedelta = DEFAULT_STATE_SOURCE_UPDATE_INTERVAL,
    ) -> None:
        """Initialize the state source coordinator.

        Args:
            hass: Home Assistant instance
            entity_id: Entity ID to monitor
            attribute: Optional attribute name to monitor
            update_interval: How often to update
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"State Source {entity_id}",
            update_interval=update_interval,
        )
        self.entity_id = entity_id
        self.attribute = attribute
        self._unsub_state_listener = None

        _LOGGER.debug(
            "State source coordinator initialized for %s (attribute: %s)",
            entity_id,
            attribute,
        )

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Set up state change listener for more responsive updates
        self._unsub_state_listener = async_track_state_change_event(
            self.hass,
            self.entity_id,
            self._handle_state_change,
        )
        _LOGGER.debug("State change listener set up for %s", self.entity_id)

    async def async_shutdown(self) -> None:
        """Shut down the coordinator."""
        if self._unsub_state_listener:
            self._unsub_state_listener()
            self._unsub_state_listener = None
        _LOGGER.debug("State source coordinator shut down for %s", self.entity_id)

    @callback
    def _handle_state_change(self, event) -> None:
        """Handle state change event."""
        _LOGGER.debug("State changed for %s, requesting refresh", self.entity_id)
        self.async_set_updated_data(self._get_current_value())

    def _get_current_value(self) -> Any:
        """Get current state or attribute value."""
        state: State | None = self.hass.states.get(self.entity_id)

        if state is None:
            _LOGGER.warning("Entity %s not found", self.entity_id)
            return None

        if state.state == "unavailable":
            _LOGGER.warning("Entity %s is unavailable", self.entity_id)
            return None

        # Get attribute if specified
        if self.attribute:
            value = state.attributes.get(self.attribute)
            if value is None:
                _LOGGER.warning(
                    "Attribute %s not found on entity %s",
                    self.attribute,
                    self.entity_id,
                )
            return value

        # Return state value
        return state.state

    async def _async_update_data(self) -> Any:
        """Fetch data from state source."""
        return self._get_current_value()

    def get_numeric_value(self, min_value: float = 0, max_value: float = 100) -> float:
        """Get value as numeric, clamped to range.

        Args:
            min_value: Minimum value
            max_value: Maximum value

        Returns:
            Numeric value clamped to range, or min_value if unavailable
        """
        value = self.data

        if value is None:
            return min_value
        
        # Check for numeric types first
        if not isinstance(value, (int, float, str)):
            _LOGGER.warning(
                "Value %s is not numeric type (%s), using min_value",
                value,
                type(value).__name__,
            )
            return min_value

        try:
            numeric_value = float(value)
            return max(min_value, min(max_value, numeric_value))
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "Could not convert value %s to numeric: %s, using min_value",
                value,
                err,
            )
            return min_value
