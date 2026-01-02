"""Number platform for WLED Effects integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_BRIGHTNESS,
    CONF_SEGMENT_ID,
    CONF_START_LED,
    CONF_STOP_LED,
    DOMAIN,
    ICON_BRIGHTNESS,
    ICON_LED,
    ICON_SEGMENT,
    NUMBER_BRIGHTNESS_MAX,
    NUMBER_BRIGHTNESS_MIN,
    NUMBER_BRIGHTNESS_STEP,
    NUMBER_LED_MAX,
    NUMBER_LED_MIN,
    NUMBER_LED_STEP,
    NUMBER_SEGMENT_MAX,
    NUMBER_SEGMENT_MIN,
    NUMBER_SEGMENT_STEP,
)
from .coordinator import EffectCoordinator
from .device import create_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLED Effects number entities from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: EffectCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        WLEDEffectBrightnessNumber(coordinator, entry),
        WLEDEffectSegmentNumber(coordinator, entry),
    ]
    
    # Add LED range entities if configured
    if CONF_START_LED in entry.options:
        entities.append(WLEDEffectStartLEDNumber(coordinator, entry))
    if CONF_STOP_LED in entry.options:
        entities.append(WLEDEffectStopLEDNumber(coordinator, entry))

    async_add_entities(entities)


class WLEDEffectNumberBase(CoordinatorEntity[EffectCoordinator], NumberEntity):
    """Base class for WLED Effect number entities."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the number entity.

        Args:
            coordinator: Effect coordinator
            entry: Config entry
            key: Configuration key
            name: Entity name
            icon: Entity icon
        """
        super().__init__(coordinator)
        
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        
        # Set device info
        wled_device_id = entry.data.get("wled_device_id", "")
        effect_type = entry.data.get("effect_type", "")
        effect_name = entry.options.get("effect_name", "Effect")
        self._attr_device_info = create_device_info(
            entry, wled_device_id, effect_name, effect_type
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.debug("Setting %s to %s", self._key, value)
        
        # Update coordinator config
        await self.coordinator.async_update_config({self._key: int(value)})


class WLEDEffectBrightnessNumber(WLEDEffectNumberBase):
    """Number entity for effect brightness."""

    _attr_native_min_value = NUMBER_BRIGHTNESS_MIN
    _attr_native_max_value = NUMBER_BRIGHTNESS_MAX
    _attr_native_step = NUMBER_BRIGHTNESS_STEP

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize brightness number."""
        super().__init__(
            coordinator,
            entry,
            CONF_BRIGHTNESS,
            "Brightness",
            ICON_BRIGHTNESS,
        )

    @property
    def native_value(self) -> float:
        """Return the current brightness."""
        return self.coordinator.effect.brightness


class WLEDEffectSegmentNumber(WLEDEffectNumberBase):
    """Number entity for segment ID."""

    _attr_native_min_value = NUMBER_SEGMENT_MIN
    _attr_native_max_value = NUMBER_SEGMENT_MAX
    _attr_native_step = NUMBER_SEGMENT_STEP
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize segment number."""
        super().__init__(
            coordinator,
            entry,
            CONF_SEGMENT_ID,
            "Segment ID",
            ICON_SEGMENT,
        )

    @property
    def native_value(self) -> float:
        """Return the current segment ID."""
        return self.coordinator.effect.segment_id


class WLEDEffectStartLEDNumber(WLEDEffectNumberBase):
    """Number entity for start LED."""

    _attr_native_min_value = NUMBER_LED_MIN
    _attr_native_max_value = NUMBER_LED_MAX
    _attr_native_step = NUMBER_LED_STEP
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize start LED number."""
        super().__init__(
            coordinator,
            entry,
            CONF_START_LED,
            "Start LED",
            ICON_LED,
        )

    @property
    def native_value(self) -> float | None:
        """Return the current start LED."""
        return self.coordinator.effect.start_led


class WLEDEffectStopLEDNumber(WLEDEffectNumberBase):
    """Number entity for stop LED."""

    _attr_native_min_value = NUMBER_LED_MIN
    _attr_native_max_value = NUMBER_LED_MAX
    _attr_native_step = NUMBER_LED_STEP
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize stop LED number."""
        super().__init__(
            coordinator,
            entry,
            CONF_STOP_LED,
            "Stop LED",
            ICON_LED,
        )

    @property
    def native_value(self) -> float | None:
        """Return the current stop LED."""
        return self.coordinator.effect.stop_led
