"""The WLED Effects integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_EFFECT_CONFIG,
    CONF_EFFECT_TYPE,
    CONF_WLED_HOST,
    DOMAIN,
)
from .coordinator import EffectCoordinator
from .effects import EFFECT_REGISTRY
from .errors import ConnectionError as WLEDConnectionError, EffectNotFoundError
from .wled_manager import WLEDConnectionManager

if TYPE_CHECKING:
    from .effects.base import WLEDEffectBase

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WLED Effects from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry for this effect

    Returns:
        True if setup successful
    """
    _LOGGER.info("Setting up WLED Effects entry: %s", entry.title)

    # Initialize domain data if not present
    hass.data.setdefault(DOMAIN, {})

    # Get or create connection manager
    if "connection_manager" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["connection_manager"] = WLEDConnectionManager(hass)

    connection_manager: WLEDConnectionManager = hass.data[DOMAIN]["connection_manager"]

    try:
        # Get WLED client
        wled_host = entry.data[CONF_WLED_HOST]
        wled_client = await connection_manager.get_client(wled_host)

        # Get JSON API client for per-LED control
        json_client = await connection_manager.get_json_client(wled_host)

        # Get effect class
        effect_type = entry.data[CONF_EFFECT_TYPE]
        effect_class = EFFECT_REGISTRY.get_effect_class(effect_type)

        # Create effect configuration
        effect_config = {
            **entry.options.get(CONF_EFFECT_CONFIG, {}),
            **entry.options,
        }

        # Instantiate effect with both clients
        effect: WLEDEffectBase = effect_class(hass, wled_client, effect_config, json_client)

        # Setup effect
        if not await effect.setup():
            raise ConfigEntryNotReady(f"Failed to setup effect {effect_type}")

        # Create coordinator
        coordinator = EffectCoordinator(hass, effect, entry)

        # Perform initial refresh
        await coordinator.async_config_entry_first_refresh()

        # Store data for this entry
        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "effect": effect,
            "wled_client": wled_client,
            "json_client": json_client,
            "wled_host": wled_host,
        }

        # Forward setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Register update listener for options changes
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        _LOGGER.info("Successfully set up WLED Effects entry: %s", entry.title)
        return True

    except WLEDConnectionError as err:
        _LOGGER.error("Failed to connect to WLED device: %s", err)
        raise ConfigEntryNotReady(f"Failed to connect to WLED device: {err}") from err

    except EffectNotFoundError as err:
        _LOGGER.error("Effect type not found: %s", err)
        # This is a configuration error, not a temporary issue
        return False

    except Exception as err:
        _LOGGER.exception("Unexpected error setting up WLED Effects: %s", err)
        raise ConfigEntryNotReady(f"Unexpected error: {err}") from err


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to unload

    Returns:
        True if unload successful
    """
    _LOGGER.info("Unloading WLED Effects entry: %s", entry.title)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Get entry data
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)

        # Stop effect if running
        effect: WLEDEffectBase = entry_data["effect"]
        if effect.running:
            try:
                await effect.stop()
            except Exception as err:
                _LOGGER.error("Error stopping effect during unload: %s", err)

        # Close JSON client
        json_client = entry_data.get("json_client")
        if json_client:
            try:
                await json_client.close()
            except Exception as err:
                _LOGGER.error("Error closing JSON client during unload: %s", err)

        # Clean up if this was the last entry (only connection_manager remains)
        if len(hass.data[DOMAIN]) == 1 and "connection_manager" in hass.data[DOMAIN]:
            connection_manager: WLEDConnectionManager = hass.data[DOMAIN].pop(
                "connection_manager"
            )
            if connection_manager:
                await connection_manager.close_all()
            # Clean up domain data if empty
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN)

        _LOGGER.info("Successfully unloaded WLED Effects entry: %s", entry.title)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change.

    Args:
        hass: Home Assistant instance
        entry: Config entry to reload
    """
    _LOGGER.info("Reloading WLED Effects entry: %s", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry being removed
    """
    _LOGGER.info("Removing WLED Effects entry: %s", entry.title)

    # Clean up device registry entry
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, entry.entry_id)}
    )
    if device_entry:
        device_registry.async_remove_device(device_entry.id)
