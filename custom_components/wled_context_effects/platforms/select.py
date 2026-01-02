"""Select platform for WLED Effects integration."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import EffectCoordinator
from ..device import create_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLED Effects select entities from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: EffectCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Get effect-specific select entities from config schema
    effect_schema = coordinator.effect.config_schema()
    entities = []
    
    for key, value_schema in effect_schema.get("properties", {}).items():
        # Check if field has enum (select options)
        if "enum" in value_schema:
            entities.append(
                WLEDEffectSelect(
                    coordinator,
                    entry,
                    key,
                    value_schema.get("description", key),
                    value_schema["enum"],
                )
            )
    
    if entities:
        async_add_entities(entities)


class WLEDEffectSelect(CoordinatorEntity[EffectCoordinator], SelectEntity):
    """Select entity for effect modes/options."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EffectCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        options: list[str],
    ) -> None:
        """Initialize the select entity.

        Args:
            coordinator: Effect coordinator
            entry: Config entry
            key: Configuration key
            name: Entity name
            options: Available options
        """
        super().__init__(coordinator)
        
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_options = options
        
        # Set device info
        wled_device_id = entry.data.get("wled_device_id", "")
        effect_type = entry.data.get("effect_type", "")
        effect_name = entry.options.get("effect_name", "Effect")
        self._attr_device_info = create_device_info(
            entry, wled_device_id, effect_name, effect_type
        )

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        return self.coordinator.effect.config.get(self._key)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug("Setting %s to %s", self._key, option)
        
        # Update coordinator config
        await self.coordinator.async_update_config({self._key: option})
