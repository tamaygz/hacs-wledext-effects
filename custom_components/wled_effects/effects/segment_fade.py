"""Segment Fade effect for WLED."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

if TYPE_CHECKING:
    from wled import WLED

    from homeassistant.core import HomeAssistant


@register_effect
class SegmentFadeEffect(WLEDEffectBase):
    """Segment fade effect that smoothly transitions between two colors.
    
    This effect fades the entire LED segment between two configurable colors
    at a configurable speed.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
    ) -> None:
        """Initialize segment fade effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
        """
        super().__init__(hass, wled_client, config)
        
        # Effect-specific configuration
        self.color1: tuple[int, int, int] = self._parse_color(
            config.get("color1", "255,0,0")
        )
        self.color2: tuple[int, int, int] = self._parse_color(
            config.get("color2", "0,0,255")
        )
        self.transition_speed: float = config.get("transition_speed", 2.0)
        self.steps: int = config.get("steps", 50)
        
        # Animation state
        self.current_step: int = 0
        self.direction: int = 1  # 1 for forward, -1 for reverse

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
            return (255, 255, 255)  # Default to white

    def _interpolate_color(
        self,
        color1: tuple[int, int, int],
        color2: tuple[int, int, int],
        position: float,
    ) -> tuple[int, int, int]:
        """Interpolate between two colors.

        Args:
            color1: First color (RGB)
            color2: Second color (RGB)
            position: Position between colors (0.0 to 1.0)

        Returns:
            Interpolated RGB color
        """
        return (
            int(color1[0] + (color2[0] - color1[0]) * position),
            int(color1[1] + (color2[1] - color1[1]) * position),
            int(color1[2] + (color2[2] - color1[2]) * position),
        )

    async def run_effect(self) -> None:
        """Render fade animation."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        # Calculate current position (0.0 to 1.0)
        position = self.current_step / self.steps
        
        # Interpolate color using base class method
        current_color = self.interpolate_color(self.color1, self.color2, position)
        
        # Send to WLED
        await self.send_wled_command(
            on=True,
            brightness=self.brightness,
            color_primary=current_color,
        )
        
        # Update step
        self.current_step += self.direction
        
        # Reverse direction at endpoints
        if self.current_step >= self.steps:
            self.direction = -1
            self.current_step = self.steps
        elif self.current_step <= 0:
            self.direction = 1
            self.current_step = 0
        
        # Control fade speed
        await asyncio.sleep(self.transition_speed / self.steps)

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for segment fade effect.

        Returns:
            JSON schema dict
        """
        schema = super().config_schema()
        
        # Add effect-specific fields
        schema["properties"].update({
            "color1": {
                "type": "string",
                "description": "First color (R,G,B format)",
                "default": "255,0,0",
            },
            "color2": {
                "type": "string",
                "description": "Second color (R,G,B format)",
                "default": "0,0,255",
            },
            "transition_speed": {
                "type": "number",
                "description": "Transition duration in seconds",
                "minimum": 0.5,
                "maximum": 10.0,
                "default": 2.0,
            },
            "steps": {
                "type": "integer",
                "description": "Number of steps in transition",
                "minimum": 10,
                "maximum": 200,
                "default": 50,
            },
        })
        
        return schema
