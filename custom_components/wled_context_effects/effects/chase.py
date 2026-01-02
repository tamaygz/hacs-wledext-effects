"""Chase/Scanner effect for WLED."""
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
class ChaseEffect(WLEDEffectBase):
    """Chase/scanner effect with moving light pattern.
    
    Creates a Knight Rider / Cylon style scanning effect or a chase pattern
    where a group of LEDs moves along the strip. Direction and speed can be
    controlled by state to represent data flow, activity, or processing.
    
    Uses per-LED control for smooth fading tails and gradient effects.
    
    Context-aware features:
    - Chase speed controlled by state (slow to fast)
    - Direction can be controlled or triggered
    - Length/width of chase pattern adjustable
    - Color can represent status/priority
    - Can reverse on trigger events
    - Activity indicator (speed = processing rate)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
        json_client=None,
    ) -> None:
        """Initialize chase effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
            json_client: Optional JSON API client for per-LED control
        """
        super().__init__(hass, wled_client, config, json_client)
        
        # Effect-specific configuration
        self.chase_color: tuple[int, int, int] = self._parse_color(
            config.get("chase_color", "255,100,0")
        )
        self.background_color: tuple[int, int, int] = self._parse_color(
            config.get("background_color", "0,0,0")
        )
        self.chase_length: int = config.get("chase_length", 5)  # LEDs in chase
        self.speed: float = config.get("speed", 0.05)  # Delay between steps
        self.fade_tail: bool = config.get("fade_tail", True)  # Fade the tail
        self.bounce: bool = config.get("bounce", True)  # Bounce at ends
        self.scan_mode: bool = config.get("scan_mode", False)  # True = scanner (fade from center)
        
        # State-reactive configuration (optional)
        self.state_entity: str | None = config.get("state_entity")
        self.state_attribute: str | None = config.get("state_attribute")
        self.state_controls: str = config.get("state_controls", "speed")  # speed, direction, length
        self.state_min: float = config.get("state_min", 0.0)
        self.state_max: float = config.get("state_max", 100.0)
        
        # Animation state
        self.position: int = 0
        self.direction: int = 1  # 1 = forward, -1 = backward
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
            return (255, 100, 0)

    async def run_effect(self) -> None:
        """Render chase animation."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        # Get state value if configured
        state_value = self._get_state_value() if self.state_entity else None
        
        # Determine current parameters based on state
        current_speed = self.speed
        current_length = self.chase_length
        
        if state_value is not None:
            if self.state_controls in ["speed", "both"]:
                # Map state to speed (0.001 to 0.5 seconds)
                current_speed = self.map_value(
                    state_value, 0.0, 1.0, 0.001, 0.5, smooth=True
                )
            if self.state_controls in ["length", "both"]:
                # Map state to chase length (1 to 20 LEDs)
                current_length = int(self.map_value(
                    state_value, 0.0, 1.0, 1.0, 20.0, smooth=True
                ))
            if self.state_controls == "direction":
                # State controls direction (below 0.5 = backward, above = forward)
                self.direction = 1 if state_value >= 0.5 else -1

        led_count = (self.stop_led - self.start_led) + 1
        
        # Generate colors based on mode
        colors: list[tuple[int, int, int]] = []
        
        if self.scan_mode:
            # Scanner mode - light emanates from position with fade
            for i in range(led_count):
                distance = abs(i - self.position)
                if distance < current_length:
                    if self.fade_tail:
                        # Fade based on distance
                        fade_factor = 1.0 - (distance / current_length)
                        color = self.interpolate_color(
                            self.background_color,
                            self.chase_color,
                            fade_factor
                        )
                    else:
                        color = self.chase_color
                    colors.append(color)
                else:
                    colors.append(self.background_color)
        else:
            # Chase mode - moving block with optional tail
            for i in range(led_count):
                # Check if LED is in chase range
                if self.direction > 0:
                    # Forward chase
                    offset = i - self.position
                    if 0 <= offset < current_length:
                        if self.fade_tail:
                            fade_factor = 1.0 - (offset / current_length)
                            color = self.interpolate_color(
                                self.background_color,
                                self.chase_color,
                                fade_factor
                            )
                        else:
                            color = self.chase_color
                        colors.append(color)
                    else:
                        colors.append(self.background_color)
                else:
                    # Backward chase
                    offset = self.position - i
                    if 0 <= offset < current_length:
                        if self.fade_tail:
                            fade_factor = 1.0 - (offset / current_length)
                            color = self.interpolate_color(
                                self.background_color,
                                self.chase_color,
                                fade_factor
                            )
                        else:
                            color = self.chase_color
                        colors.append(color)
                    else:
                        colors.append(self.background_color)
        
        # Apply reverse direction if configured (different from chase direction)
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
                    color_primary=self.chase_color,
                )
        else:
            # No JSON client - use basic command
            await self.send_wled_command(
                on=True,
                brightness=self.brightness,
                color_primary=self.chase_color,
            )
        
        # Update position
        self.position += self.direction
        
        # Handle boundaries
        if self.bounce:
            # Bounce at edges
            if self.position >= led_count - 1:
                self.position = led_count - 1
                self.direction = -1
            elif self.position <= 0:
                self.position = 0
                self.direction = 1
        else:
            # Wrap around
            if self.position >= led_count:
                self.position = 0
            elif self.position < 0:
                self.position = led_count - 1
        
        # Control update rate
        await asyncio.sleep(current_speed)

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for chase effect.

        Returns:
            JSON schema dict
        """
        schema = super().config_schema()
        
        # Add effect-specific fields
        schema["properties"].update({
            "chase_color": {
                "type": "string",
                "description": "Chase color (R,G,B format)",
                "default": "255,100,0",
            },
            "background_color": {
                "type": "string",
                "description": "Background color (R,G,B format)",
                "default": "0,0,0",
            },
            "chase_length": {
                "type": "integer",
                "description": "Length of chase in LEDs",
                "minimum": 1,
                "maximum": 50,
                "default": 5,
            },
            "speed": {
                "type": "number",
                "description": "Movement speed (delay between steps)",
                "minimum": 0.001,
                "maximum": 1.0,
                "default": 0.05,
            },
            "fade_tail": {
                "type": "boolean",
                "description": "Fade the tail of the chase",
                "default": True,
            },
            "bounce": {
                "type": "boolean",
                "description": "Bounce at ends (vs wrap around)",
                "default": True,
            },
            "scan_mode": {
                "type": "boolean",
                "description": "Scanner mode (Cylon/KITT style)",
                "default": False,
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
                "enum": ["speed", "direction", "length", "both"],
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
