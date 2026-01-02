"""Button platform for WLED Effects integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN, ICON_RUN_ONCE
from ..coordinator import EffectCoordinator
from ..device import create_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLED Effects button entities from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: EffectCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([WLEDEffectRunOnceButton(coordinator, entry)])


class WLEDEffectRunOnceButton(CoordinatorEntity[EffectCoordinator], ButtonEntity):
    """Button entity to run effect once."""

    _attr_has_entity_name = True
    _attr_icon = ICON_RUN_ONCE

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button entity.

        Args:
            coordinator: Effect coordinator
            entry: Config entry
        """
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.entry_id}_run_once"
        self._attr_name = "Run Once"
        
        # Set device info
        wled_device_id = entry.data.get("wled_device_id", "")
        effect_type = entry.data.get("effect_type", "")
        effect_name = entry.options.get("effect_name", "Effect")
        self._attr_device_info = create_device_info(
            entry, wled_device_id, effect_name, effect_type
        )

    async def async_press(self) -> None:
        """Handle button press - run effect once."""
        _LOGGER.debug("Running effect %s once", self.coordinator.effect.get_effect_name())
        await self.coordinator.async_run_once()
