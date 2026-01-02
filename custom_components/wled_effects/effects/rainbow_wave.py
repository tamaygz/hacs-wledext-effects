"""Rainbow Wave effect for WLED."""
from __future__ import annotations

import asyncio
import colorsys
from typing import TYPE_CHECKING, Any

from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

if TYPE_CHECKING:
    from wled import WLED

    from homeassistant.core import HomeAssistant


@register_effect
class RainbowWaveEffect(WLEDEffectBase):
    """Rainbow wave effect that creates an animated rainbow across the LED strip.
    
    This effect generates a smooth rainbow gradient that moves across the LED strip.
    The wave speed determines how fast the colors shift and move.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
    ) -> None:
        """Initialize rainbow wave effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
        """
        super().__init__(hass, wled_client, config)
        
        # Effect-specific configuration
        self.wave_speed: float = config.get("wave_speed", 1.0)
        self.wave_length: int = config.get("wave_length", 60)
        self.update_interval: float = config.get("update_interval", 0.05)
        
        # Animation state
        self.color_offset: float = 0.0

    async def run_effect(self) -> None:
        """Render rainbow wave animation."""
        # Generate rainbow colors for each LED
        colors: list[tuple[int, int, int]] = []
        
        led_count = (self.stop_led - self.start_led) + 1
        
        for i in range(led_count):
            # Calculate hue based on position and offset
            hue = ((i / self.wave_length) + self.color_offset) % 1.0
            
            # Convert HSV to RGB (full saturation and value)
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            
            # Scale to 0-255 range
            color = (
                int(rgb[0] * 255),
                int(rgb[1] * 255),
                int(rgb[2] * 255),
            )
            colors.append(color)

        # Send colors to WLED device
        # For individual LED control, we need to set each LED
        leds_dict = {
            self.start_led + i: colors[i]
            for i in range(led_count)
        }
        
        await self.send_wled_command(
            on=True,
            brightness=self.brightness,
            color_primary=colors[0] if colors else (255, 0, 0),  # Fallback
        )

        # Advance the wave
        self.color_offset = (self.color_offset + (self.wave_speed / 100.0)) % 1.0
        
        # Control update rate
        await asyncio.sleep(self.update_interval)

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for rainbow wave effect.

        Returns:
            JSON schema dict
        """
        schema = super().config_schema()
        
        # Add effect-specific fields
        schema["properties"].update({
            "wave_speed": {
                "type": "number",
                "description": "Speed of the wave animation (1-100)",
                "minimum": 1.0,
                "maximum": 100.0,
                "default": 10.0,
            },
            "wave_length": {
                "type": "integer",
                "description": "Length of one complete rainbow cycle in LEDs",
                "minimum": 10,
                "maximum": 500,
                "default": 60,
            },
            "update_interval": {
                "type": "number",
                "description": "Time between updates in seconds",
                "minimum": 0.01,
                "maximum": 1.0,
                "default": 0.05,
            },
        })
        
        return schema
