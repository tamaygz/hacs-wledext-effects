"""State Sync effect for WLED."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

if TYPE_CHECKING:
    from wled import WLED

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@register_effect
class StateSyncEffect(WLEDEffectBase):
    """State sync effect that visualizes Home Assistant entity states on LEDs.
    
    This effect monitors a Home Assistant entity's state and represents it
    visually on the LED strip. Supports multiple animation modes.
    
    Uses per-LED control for accurate fill visualizations.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
        json_client=None,
    ) -> None:
        """Initialize state sync effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
            json_client: Optional JSON API client for per-LED control
        """
        super().__init__(hass, wled_client, config, json_client)
        
        # Effect-specific configuration
        self.min_value: float = config.get("min_value", 0.0)
        self.max_value: float = config.get("max_value", 100.0)
        self.animation_mode: str = config.get("animation_mode", "fill")
        self.color_low: tuple[int, int, int] = self._parse_color(
            config.get("color_low", "255,0,0")
        )
        self.color_high: tuple[int, int, int] = self._parse_color(
            config.get("color_high", "0,255,0")
        )
        self.update_interval: float = config.get("update_interval", 0.05)

    async def setup(self) -> bool:
        """Setup effect."""
        return await super().setup()

    def _get_current_value(self) -> float:
        """Get current state value as percentage.

        Returns:
            Value between 0.0 and 1.0
        """
        if not self.state_coordinator:
            return 0.5  # Default to middle
        
        raw_value = self.state_coordinator.get_numeric_value(
            self.min_value, self.max_value
        )
        
        # Normalize to 0-1 range
        value_range = self.max_value - self.min_value
        if value_range <= 0:
            return 0.5
        
        return (raw_value - self.min_value) / value_range

    async def run_effect(self) -> None:
        """Render state visualization."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        # Get current value (0.0 to 1.0)
        value = self._get_current_value()

        # Apply smoothing if enabled
        if self.value_smoother:
            value = self.value_smoother.smooth(value)
        
        led_count = (self.stop_led - self.start_led) + 1
        lit_count = int(led_count * value)
        
        # Use base class color interpolation
        current_color = self.interpolate_color(self.color_low, self.color_high, value)
        
        if self.animation_mode == "fill":
            # Fill from start to position
            colors: list[tuple[int, int, int]] = []
            for i in range(led_count):
                if i < lit_count:
                    colors.append(current_color)
                else:
                    colors.append((0, 0, 0))
        
        elif self.animation_mode == "center":
            # Fill from center outward
            center = led_count // 2
            spread = int((led_count / 2) * value)
            colors = []
            for i in range(led_count):
                distance_from_center = abs(i - center)
                if distance_from_center < spread:
                    colors.append(current_color)
                else:
                    colors.append((0, 0, 0))
        
        elif self.animation_mode == "dual":
            # Fill from both ends toward center
            spread = int((led_count / 2) * value)
            colors = []
            for i in range(led_count):
                if i < spread or i >= (led_count - spread):
                    colors.append(current_color)
                else:
                    colors.append((0, 0, 0))
        
        else:  # solid
            # Entire strip same color based on value
            colors = [current_color] * led_count
        
        # Apply reverse if configured
        colors = self.apply_reverse(colors)
        
        # Use per-LED control if JSON client available
        if self.json_client:
            try:
                await self.set_individual_leds(colors)
            except Exception as err:
                _LOGGER.warning("Per-LED control failed, using fallback: %s", err)
                await self.send_wled_command(
                    on=True,
                    brightness=self.brightness,
                    color_primary=current_color,
                )
        else:
            # No JSON client - use basic command
            await self.send_wled_command(
                on=True,
                brightness=self.brightness,
                color_primary=current_color,
            )
        
        # Control update rate
        await asyncio.sleep(self.update_interval)

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for state sync effect.

        Returns:
            JSON schema dict
        """
        schema = super().config_schema()
        
        # Add effect-specific fields
        schema["properties"].update({
            "state_entity": {
                "type": "string",
                "description": "Entity ID to monitor",
            },
            "state_attribute": {
                "type": "string",
                "description": "Optional attribute to monitor",
            },
            "min_value": {
                "type": "number",
                "description": "Minimum expected value",
                "default": 0.0,
            },
            "max_value": {
                "type": "number",
                "description": "Maximum expected value",
                "default": 100.0,
            },
            "animation_mode": {
                "type": "string",
                "description": "Animation mode",
                "enum": ["fill", "center", "dual", "solid"],
                "default": "fill",
            },
            "color_low": {
                "type": "string",
                "description": "Color for low values (R,G,B)",
                "default": "255,0,0",
            },
            "color_high": {
                "type": "string",
                "description": "Color for high values (R,G,B)",
                "default": "0,255,0",
            },
            "update_interval": {
                "type": "number",
                "description": "Update interval in seconds",
                "minimum": 0.01,
                "maximum": 5.0,
                "default": 0.05,
            },
        })
        
        schema["required"].append("state_entity")
        
        return schema
    
    def reload_config(self) -> None:
        """Reload configuration from self.config dictionary."""
        super().reload_config()
        
        # Reload effect-specific config
        self.state_entity = self.config.get("state_entity", "")
        self.state_attribute = self.config.get("state_attribute")
        self.min_value = self.config.get("min_value", 0.0)
        self.max_value = self.config.get("max_value", 100.0)
        self.animation_mode = self.config.get("animation_mode", "fill")
        self.color_low = self._parse_color(
            self.config.get("color_low", "255,0,0")
        )
        self.color_high = self._parse_color(
            self.config.get("color_high", "0,255,0")
        )
        self.update_interval = self.config.get("update_interval", 0.05)
