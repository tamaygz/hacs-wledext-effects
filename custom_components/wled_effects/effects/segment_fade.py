"""Segment Fade effect for WLED."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from ..coordinator import StateSourceCoordinator
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
        
        # State-reactive configuration (optional)
        self.state_entity: str | None = config.get("state_entity")
        self.state_attribute: str | None = config.get("state_attribute")
        self.state_controls: str = config.get("state_controls", "speed")  # speed, position
        self.state_min: float = config.get("state_min", 0.0)
        self.state_max: float = config.get("state_max", 100.0)
        
        # Animation state
        self.current_step: int = 0
        self.direction: int = 1  # 1 for forward, -1 for reverse
        self.state_coordinator: StateSourceCoordinator | None = None

    async def setup(self) -> bool:
        """Setup effect with optional state coordinator."""
        if not await super().setup():
            return False
        
        # Create state coordinator if entity specified
        if self.state_entity:
            self.state_coordinator = StateSourceCoordinator(
                self.hass,
                self.state_entity,
                self.state_attribute,
            )
            await self.state_coordinator.async_setup()
            await self.state_coordinator.async_config_entry_first_refresh()
        
        return True

    async def stop(self) -> None:
        """Stop effect and cleanup state coordinator."""
        await super().stop()
        
        if self.state_coordinator:
            await self.state_coordinator.async_shutdown()

    def _get_state_value(self) -> float:
        """Get normalized state value (0.0 to 1.0)."""
        if not self.state_coordinator:
            return 0.5  # Default middle value
        
        raw_value = self.state_coordinator.get_numeric_value(
            self.state_min, self.state_max
        )
        
        # Normalize to 0-1
        value_range = self.state_max - self.state_min
        if value_range <= 0:
            return 0.5
        
        normalized = (raw_value - self.state_min) / value_range
        return max(0.0, min(1.0, normalized))

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

        # Get state value if configured
        state_value = self._get_state_value() if self.state_entity else None
        
        # Calculate current position
        if state_value is not None and self.state_controls == "position":
            # State directly controls position in fade cycle
            position = state_value
            # No auto-advancement when state controls position
        else:
            # Normal auto-cycling behavior
            position = self.current_step / self.steps
            
            # Update step for next iteration
            self.current_step += self.direction
            
            # Reverse direction at endpoints
            if self.current_step >= self.steps:
                self.direction = -1
                self.current_step = self.steps
            elif self.current_step <= 0:
                self.direction = 1
                self.current_step = 0
        
        # Interpolate color using base class method
        current_color = self.interpolate_color(self.color1, self.color2, position)
        
        # Send to WLED
        await self.send_wled_command(
            on=True,
            brightness=self.brightness,
            color_primary=current_color,
        )
        
        # Control fade speed (modulate by state if configured)
        speed_multiplier = 1.0
        if state_value is not None and self.state_controls == "speed":
            # Map state to speed multiplier (0.1 to 10.0)
            speed_multiplier = self.map_value(
                state_value, 0.0, 1.0, 0.1, 10.0, smooth=True
            )
        
        await asyncio.sleep((self.transition_speed / self.steps) / speed_multiplier)

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
            "state_entity": {
                "type": "string",
                "description": "Optional: Entity ID to control effect parameters",
            },
            "state_attribute": {
                "type": "string",
                "description": "Optional: Attribute to monitor",
            },
            "state_controls": {
                "type": "string",
                "description": "What parameter state controls",
                "enum": ["speed", "position"],
                "default": "speed",
            },
            "state_min": {
                "type": "number",
                "description": "Minimum state value",
                "default": 0.0,
            },
            "state_max": {
                "type": "number",
                "description": "Maximum state value",
                "default": 100.0,
            },
        })
        
        return schema
