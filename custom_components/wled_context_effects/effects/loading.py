"""Loading effect for WLED."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from ..coordinator import StateSourceCoordinator
from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

if TYPE_CHECKING:
    from wled import WLED

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@register_effect
class LoadingEffect(WLEDEffectBase):
    """Loading bar effect that moves across the LED strip.
    
    This effect creates a moving "loading bar" or "knight rider" style animation
    with a configurable size and speed.
    
    Uses per-LED control for smooth gradient trails.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
        json_client=None,
    ) -> None:
        """Initialize loading effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
            json_client: Optional JSON API client for per-LED control
        """
        super().__init__(hass, wled_client, config, json_client)
        
        # Effect-specific configuration
        self.color: tuple[int, int, int] = self._parse_color(
            config.get("color", "0,255,0")
        )
        self.bar_size: int = config.get("bar_size", 5)
        self.speed: float = config.get("speed", 0.1)
        self.trail_fade: bool = config.get("trail_fade", True)
        
        # State-reactive configuration (optional)
        self.state_entity: str | None = config.get("state_entity")
        self.state_attribute: str | None = config.get("state_attribute")
        self.state_controls: str = config.get("state_controls", "speed")  # speed, position, bar_size
        self.state_min: float = config.get("state_min", 0.0)
        self.state_max: float = config.get("state_max", 100.0)
        
        # Animation state
        self.position: int = 0
        self.direction: int = 1
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
            return (0, 255, 0)  # Default to green

    async def run_effect(self) -> None:
        """Render loading bar animation."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        # Get state value if configured
        state_value = self._get_state_value() if self.state_entity else None
        
        led_count = (self.stop_led - self.start_led) + 1
        
        # Determine current position
        if state_value is not None and self.state_controls == "position":
            # State directly controls position
            self.position = int(state_value * (led_count - 1))
        else:
            # Normal auto-cycling behavior - position updated at end
            pass
        
        # Determine bar size
        current_bar_size = self.bar_size
        if state_value is not None and self.state_controls == "bar_size":
            # Map state to bar size (1 to 50)
            current_bar_size = int(self.map_value(
                state_value, 0.0, 1.0, 1.0, 50.0, smooth=True
            ))
        
        # Calculate which LEDs should be lit
        colors: list[tuple[int, int, int]] = []
        
        for i in range(led_count):
            # Distance from current position
            distance = abs(i - self.position)
            
            if distance < current_bar_size:
                if self.trail_fade:
                    # Fade based on distance
                    fade_factor = 1.0 - (distance / current_bar_size)
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

        # Use per-LED control if JSON client available
        if self.json_client:
            try:
                await self.set_individual_leds(colors)
            except Exception as err:
                _LOGGER.warning("Per-LED control failed, using fallback: %s", err)
                await self.send_wled_command(
                    on=True,
                    brightness=self.brightness,
                    color_primary=self.color,
                )
        else:
            # No JSON client - use basic command
            await self.send_wled_command(
                on=True,
                brightness=self.brightness,
                color_primary=self.color,
            )
        
        # Update position if not controlled by state
        if state_value is None or self.state_controls != "position":
            self.position += self.direction
            
            # Bounce at endpoints
            if self.position >= led_count - 1:
                self.direction = -1
                self.position = led_count - 1
            elif self.position <= 0:
                self.direction = 1
                self.position = 0
        
        # Control speed (modulate by state if configured)
        current_speed = self.speed
        if state_value is not None and self.state_controls == "speed":
            # Map state to speed multiplier (0.01 to 1.0)
            current_speed = self.map_value(
                state_value, 0.0, 1.0, 0.01, 1.0, smooth=True
            )
        
        await asyncio.sleep(current_speed)

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
                "enum": ["speed", "position", "bar_size"],
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
