"""Sensor platform for WLED Effects integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_LAST_ERROR,
    ATTR_SUCCESS_RATE,
    DOMAIN,
    ICON_ERROR,
    STATE_ERROR,
    STATE_RUNNING,
    STATE_STOPPED,
    UNIT_PERCENT,
)
from .coordinator import EffectCoordinator
from .device import create_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLED Effects sensor entities from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: EffectCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([
        WLEDEffectStatusSensor(coordinator, entry),
        WLEDEffectSuccessRateSensor(coordinator, entry),
        WLEDEffectLastErrorSensor(coordinator, entry),
    ])


class WLEDEffectSensorBase(CoordinatorEntity[EffectCoordinator], SensorEntity):
    """Base class for WLED Effect sensor entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        """Initialize the sensor entity.

        Args:
            coordinator: Effect coordinator
            entry: Config entry
            key: Sensor key
            name: Entity name
        """
        super().__init__(coordinator)
        
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        
        # Set device info
        wled_device_id = entry.data.get("wled_device_id", "")
        effect_type = entry.data.get("effect_type", "")
        effect_name = entry.options.get("effect_name", "Effect")
        self._attr_device_info = create_device_info(
            entry, wled_device_id, effect_name, effect_type
        )


class WLEDEffectStatusSensor(WLEDEffectSensorBase):
    """Sensor entity for effect status."""

    _attr_icon = "mdi:information"

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize status sensor."""
        super().__init__(coordinator, entry, "status", "Status")

    @property
    def native_value(self) -> str:
        """Return the current status."""
        data = self.coordinator.data
        
        if data.get("last_error"):
            return STATE_ERROR
        elif data.get("running"):
            return STATE_RUNNING
        else:
            return STATE_STOPPED

    @property
    def icon(self) -> str:
        """Return icon based on status."""
        if self.native_value == STATE_ERROR:
            return ICON_ERROR
        return self._attr_icon


class WLEDEffectSuccessRateSensor(WLEDEffectSensorBase):
    """Sensor entity for command success rate."""

    _attr_icon = "mdi:chart-line"
    _attr_native_unit_of_measurement = UNIT_PERCENT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize success rate sensor."""
        super().__init__(coordinator, entry, "success_rate", "Success Rate")

    @property
    def native_value(self) -> float:
        """Return the success rate."""
        stats = self.coordinator.data.get("statistics", {})
        return round(stats.get(ATTR_SUCCESS_RATE, 100.0), 1)


class WLEDEffectLastErrorSensor(WLEDEffectSensorBase):
    """Sensor entity for last error."""

    _attr_icon = ICON_ERROR

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize last error sensor."""
        super().__init__(coordinator, entry, "last_error", "Last Error")

    @property
    def native_value(self) -> str:
        """Return the last error."""
        stats = self.coordinator.data.get("statistics", {})
        error = stats.get(ATTR_LAST_ERROR)
        return error if error else "None"
