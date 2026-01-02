"""Loading effect for WLED."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

if TYPE_CHECKING:
    from wled import WLED

    from homeassistant.core import HomeAssistant


@register_effect
class LoadingEffect(WLEDEffectBase):
    """Loading bar effect that moves across the LED strip.
    
    This effect creates a moving "loading bar" or "knight rider" style animation
    with a configurable size and speed.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
    ) -> None:
        """Initialize loading effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
        """
        super().__init__(hass, wled_client, config)
        
        # Effect-specific configuration
        self.color: tuple[int, int, int] = self._parse_color(
            config.get("color", "0,255,0")
        )
        self.bar_size: int = config.get("bar_size", 5)
        self.speed: float = config.get("speed", 0.1)
        self.trail_fade: bool = config.get("trail_fade", True)
        
        # Animation state
        self.position: int = 0
        self.direction: int = 1

    def _parse_color(self, color_str: str) -> tuple[int, int, int]:
        """Parse color from string format.

        Args:
            color_str: Color in format "R,G,B"

        Returns:
            RGB tuple
        """
        try:
            parts = color_str.split(",")
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return (0, 255, 0)  # Default to green

    async def run_effect(self) -> None:
        """Render loading bar animation."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        led_count = (self.stop_led - self.start_led) + 1
        
        # Calculate which LEDs should be lit
        colors: list[tuple[int, int, int]] = []
        
        for i in range(led_count):
            # Distance from current position
            distance = abs(i - self.position)
            
            if distance < self.bar_size:
                if self.trail_fade:
                    # Fade based on distance
                    fade_factor = 1.0 - (distance / self.bar_size)
                    color = (
                        int(self.color[0] * fade_factor),
                        int(self.color[1] * fade_factor),
                        int(self.color[2] * fade_factor),
                    )
                else:
                    color = self.color
                colors.append(color)
            else:
                colors.append((0, 0, 0))  # Off
        
        # Apply reverse direction if configured
        colors = self.apply_reverse(colors)

        # Send to WLED - set primary color to the main bar color
        await self.send_wled_command(
            on=True,
            brightness=self.brightness,
            color_primary=self.color,
        )
        
        # Update position
        self.position += self.direction
        
        # Bounce at endpoints
        if self.position >= led_count - 1:
            self.direction = -1
            self.position = led_count - 1
        elif self.position <= 0:
            self.direction = 1
            self.position = 0
        
        # Control speed
        await asyncio.sleep(self.speed)

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for loading effect.

        Returns:
            JSON schema dict
        """
        schema = super().config_schema()
        
        # Add effect-specific fields
        schema["properties"].update({
            "color": {
                "type": "string",
                "description": "Bar color (R,G,B format)",
                "default": "0,255,0",
            },
            "bar_size": {
                "type": "integer",
                "description": "Size of the loading bar in LEDs",
                "minimum": 1,
                "maximum": 50,
                "default": 5,
            },
            "speed": {
                "type": "number",
                "description": "Movement speed (delay between steps in seconds)",
                "minimum": 0.01,
                "maximum": 1.0,
                "default": 0.1,
            },
            "trail_fade": {
                "type": "boolean",
                "description": "Fade the trail behind the bar",
                "default": True,
            },
        })
        
        return schema
