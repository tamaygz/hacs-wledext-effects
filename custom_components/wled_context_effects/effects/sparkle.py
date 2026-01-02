"""Sparkle/Twinkle effect for WLED."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING, Any

from ..coordinator import StateSourceCoordinator
from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

if TYPE_CHECKING:
    from wled import WLED

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@register_effect
class SparkleEffect(WLEDEffectBase):
    """Sparkle/twinkle effect with random pixel illumination.
    
    Creates a twinkling starfield effect where random pixels light up
    and fade out. Density and speed can be controlled by state to represent
    activity levels, notification counts, or ambient conditions.
    
    Uses per-LED control for individual sparkle brightness tracking.
    
    Context-aware features:
    - Sparkle density controlled by state (sparse to dense)
    - Twinkle speed controlled by state (slow to fast)
    - Color can represent event/notification type
    - Can burst sparkles on trigger events
    - Activity visualization (more activity = more sparkles)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
        json_client=None,
    ) -> None:
        """Initialize sparkle effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
            json_client: Optional JSON API client for per-LED control
        """
        super().__init__(hass, wled_client, config, json_client)
        
        # Effect-specific configuration
        self.sparkle_color: tuple[int, int, int] = self._parse_color(
            config.get("sparkle_color", "255,255,255")
        )
        self.background_color: tuple[int, int, int] = self._parse_color(
            config.get("background_color", "0,0,20")
        )
        self.density: float = config.get("density", 0.1)  # 0.0 to 1.0 (percentage of LEDs)
        self.fade_rate: float = config.get("fade_rate", 0.8)  # How fast sparkles fade (0.0 to 1.0)
        self.color_variation: bool = config.get("color_variation", False)  # Random hue variation
        
        # State-reactive configuration (optional)
        self.state_entity: str | None = config.get("state_entity")
        self.state_attribute: str | None = config.get("state_attribute")
        self.state_controls: str = config.get("state_controls", "density")  # density, speed, both
        self.state_min: float = config.get("state_min", 0.0)
        self.state_max: float = config.get("state_max", 100.0)
        
        # Animation state - track brightness of each LED
        self.led_brightness: list[float] = []
        self.state_coordinator: StateSourceCoordinator | None = None

    async def setup(self) -> bool:
        """Setup effect with optional state coordinator."""
        if not await super().setup():
            return False
        
        # Initialize LED brightness tracking
        led_count = (self.stop_led - self.start_led) + 1
        self.led_brightness = [0.0] * led_count
        
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
            return (255, 255, 255)

    def _vary_color(self, base_color: tuple[int, int, int]) -> tuple[int, int, int]:
        """Add random hue variation to color.

        Args:
            base_color: Base RGB color

        Returns:
            Varied RGB color
        """
        if not self.color_variation:
            return base_color
        
        # Convert to HSV, vary hue, convert back
        import colorsys
        r, g, b = [c / 255.0 for c in base_color]
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        
        # Vary hue by +/- 0.1
        h = (h + random.uniform(-0.1, 0.1)) % 1.0
        
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (int(r * 255), int(g * 255), int(b * 255))

    async def run_effect(self) -> None:
        """Render sparkle animation."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        # Get state value if configured
        state_value = self._get_state_value() if self.state_entity else None
        
        # Determine current density and fade rate based on state
        current_density = self.density
        current_fade_rate = self.fade_rate
        
        if state_value is not None:
            if self.state_controls in ["density", "both"]:
                # Map state to density (0.01 to 1.0)
                current_density = self.map_value(
                    state_value, 0.0, 1.0, 0.01, 1.0, smooth=True
                )
            if self.state_controls in ["speed", "both"]:
                # Map state to fade rate (slower fade = more visible sparkles)
                current_fade_rate = self.map_value(
                    state_value, 0.0, 1.0, 0.95, 0.5, smooth=True
                )

        led_count = len(self.led_brightness)
        
        # Randomly activate new sparkles based on density
        sparkles_to_add = int(led_count * current_density * 0.1)  # 10% chance per frame
        for _ in range(sparkles_to_add):
            led_idx = random.randint(0, led_count - 1)
            # Set to full brightness
            self.led_brightness[led_idx] = 1.0
        
        # Fade all LEDs
        for i in range(led_count):
            if self.led_brightness[i] > 0:
                self.led_brightness[i] *= current_fade_rate
                # Clean up very dim LEDs
                if self.led_brightness[i] < 0.01:
                    self.led_brightness[i] = 0.0
        
        # Generate colors
        colors: list[tuple[int, int, int]] = []
        for brightness in self.led_brightness:
            if brightness > 0:
                # Interpolate between background and sparkle color
                sparkle_color = self._vary_color(self.sparkle_color)
                color = self.interpolate_color(
                    self.background_color, 
                    sparkle_color, 
                    brightness
                )
                colors.append(color)
            else:
                colors.append(self.background_color)
        
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
                    color_primary=self.sparkle_color,
                )
        else:
            # No JSON client - use basic command
            await self.send_wled_command(
                on=True,
                brightness=self.brightness,
                color_primary=self.sparkle_color,
            )
        
        # Control update rate
        await asyncio.sleep(0.03)

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for sparkle effect.

        Returns:
            JSON schema dict
        """
        schema = super().config_schema()
        
        # Add effect-specific fields
        schema["properties"].update({
            "sparkle_color": {
                "type": "string",
                "description": "Sparkle color (R,G,B format)",
                "default": "255,255,255",
            },
            "background_color": {
                "type": "string",
                "description": "Background color (R,G,B format)",
                "default": "0,0,20",
            },
            "density": {
                "type": "number",
                "description": "Sparkle density (0.0 to 1.0)",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.1,
            },
            "fade_rate": {
                "type": "number",
                "description": "How fast sparkles fade (0.0 to 1.0)",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.8,
            },
            "color_variation": {
                "type": "boolean",
                "description": "Enable random color hue variation",
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
                "enum": ["density", "speed", "both"],
                "default": "density",
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
