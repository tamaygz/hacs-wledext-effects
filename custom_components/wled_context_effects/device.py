"""Device info helpers for WLED Effects integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

WLED_DOMAIN = "wled"


def create_device_info(
    entry: ConfigEntry,
    wled_device_id: str,
    effect_name: str,
    effect_type: str,
) -> DeviceInfo:
    """Create device info for an effect.

    Args:
        entry: Config entry for the effect
        wled_device_id: Unique ID of the parent WLED device (from WLED integration)
        effect_name: User-friendly name of the effect
        effect_type: Type/class name of the effect

    Returns:
        DeviceInfo dict
    """
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"{effect_name} Effect",
        manufacturer="WLED Effects",
        model=effect_type,
        configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}",
    )
    
    # Link to parent WLED device if we have the unique_id
    if wled_device_id:
        device_info["via_device"] = (WLED_DOMAIN, wled_device_id)
    
    return device_info
