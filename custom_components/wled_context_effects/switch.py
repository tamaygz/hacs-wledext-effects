"""Switch platform for WLED Effects integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_COMMAND_COUNT,
    ATTR_EFFECT_TYPE,
    ATTR_FAILURE_COUNT,
    ATTR_LAST_ERROR,
    ATTR_LAST_STARTED,
    ATTR_LAST_STOPPED,
    ATTR_RUNNING_TIME,
    ATTR_SEGMENT_ID,
    ATTR_SUCCESS_COUNT,
    ATTR_SUCCESS_RATE,
    CONF_EFFECT_NAME,
    CONF_WLED_UNIQUE_ID,
    DOMAIN,
    ICON_EFFECT,
    ICON_RUNNING,
    ICON_STOPPED,
)
from .coordinator import EffectCoordinator
from .device import create_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLED Effects switch from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: EffectCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([WLEDEffectSwitch(coordinator, entry)])


class WLEDEffectSwitch(CoordinatorEntity[EffectCoordinator], SwitchEntity):
    """Representation of a WLED Effect switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch.

        Args:
            coordinator: Effect coordinator
            entry: Config entry
        """
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.entry_id}_switch"
        self._attr_name = entry.options.get(CONF_EFFECT_NAME, "Effect")
        
        # Set device info
        wled_unique_id = entry.data.get(CONF_WLED_UNIQUE_ID, "")
        effect_type = entry.data.get("effect_type", "")
        self._attr_device_info = create_device_info(
            entry, wled_unique_id, self._attr_name, effect_type
        )

    @property
    def is_on(self) -> bool:
        """Return true if effect is running."""
        return self.coordinator.data.get("running", False)

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        if self.is_on:
            return ICON_RUNNING
        return ICON_STOPPED

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        data = self.coordinator.data
        stats = data.get("statistics", {})
        
        attributes = {
            ATTR_EFFECT_TYPE: data.get("effect_type"),
            ATTR_SEGMENT_ID: self.coordinator.effect.segment_id,
        }
        
        # Add statistics
        if stats:
            attributes.update({
                ATTR_COMMAND_COUNT: stats.get(ATTR_COMMAND_COUNT, 0),
                ATTR_SUCCESS_COUNT: stats.get(ATTR_SUCCESS_COUNT, 0),
                ATTR_FAILURE_COUNT: stats.get(ATTR_FAILURE_COUNT, 0),
                ATTR_SUCCESS_RATE: round(stats.get(ATTR_SUCCESS_RATE, 100.0), 1),
                ATTR_LAST_ERROR: stats.get(ATTR_LAST_ERROR),
            })
        
        # Add timing information
        if data.get("last_started"):
            attributes[ATTR_LAST_STARTED] = data["last_started"].isoformat()
        if data.get("last_stopped"):
            attributes[ATTR_LAST_STOPPED] = data["last_stopped"].isoformat()
        if data.get("running_time"):
            attributes[ATTR_RUNNING_TIME] = round(data["running_time"], 1)
        
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the effect."""
        _LOGGER.debug("Turning on effect %s", self._attr_name)
        await self.coordinator.async_start_effect()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the effect."""
        _LOGGER.debug("Turning off effect %s", self._attr_name)
        await self.coordinator.async_stop_effect()
