"""Rainbow Wave effect for WLED."""
from __future__ import annotations

import asyncio
import colorsys
from typing import TYPE_CHECKING, Any

from ..coordinator import StateSourceCoordinator
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
    
    Uses per-LED control for true rainbow gradients.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
        json_client=None,
    ) -> None:
        """Initialize rainbow wave effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
            json_client: Optional JSON API client for per-LED control
        """
        super().__init__(hass, wled_client, config, json_client)
        
        # Effect-specific configuration
        self.wave_speed: float = config.get("wave_speed", 1.0)
        self.wave_length: int = config.get("wave_length", 60)
        self.update_interval: float = config.get("update_interval", 0.03)
        
        # State-reactive configuration (optional)
        self.state_entity: str | None = config.get("state_entity")
        self.state_attribute: str | None = config.get("state_attribute")
        self.state_controls: str = config.get("state_controls", "speed")  # speed, wavelength, both
        self.state_min: float = config.get("state_min", 0.0)
        self.state_max: float = config.get("state_max", 100.0)
        
        # Animation state
        self.color_offset: float = 0.0
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

    async def run_effect(self) -> None:
        """Render rainbow wave animation."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        # Get state value if configured
        state_value = self._get_state_value() if self.state_entity else None
        
        # Modulate parameters based on state
        current_speed = self.wave_speed
        current_wavelength = self.wave_length
        
        if state_value is not None:
            if self.state_controls in ["speed", "both"]:
                # Map state to speed (0.1 to 100)
                current_speed = self.map_value(
                    state_value, 0.0, 1.0, 1.0, 100.0, smooth=True
                )
            if self.state_controls in ["wavelength", "both"]:
                # Map state to wavelength (10 to 200)
                current_wavelength = int(self.map_value(
                    state_value, 0.0, 1.0, 10.0, 200.0, smooth=True
                ))

        # Generate rainbow colors for each LED
        colors: list[tuple[int, int, int]] = []
        
        led_count = (self.stop_led - self.start_led) + 1
        
        for i in range(led_count):
            # Calculate hue based on position and offset
            hue = ((i / current_wavelength) + self.color_offset) % 1.0
            
            # Convert HSV to RGB (full saturation and value)
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            
            # Scale to 0-255 range
            color = (
                int(rgb[0] * 255),
                int(rgb[1] * 255),
                int(rgb[2] * 255),
            )
            colors.append(color)

        # Apply reverse direction if configured
        colors = self.apply_reverse(colors)

        # Use per-LED control if JSON client available
        if self.json_client:
            try:
                await self.set_individual_leds(colors)
            except Exception as err:
                # Fallback to basic command if per-LED fails
                primary_color = colors[0] if colors else (255, 0, 0)
                await self.send_wled_command(
                    on=True,
                    brightness=self.brightness,
                    color_primary=primary_color,
                )
        else:
            # No JSON client - use basic command with first color
            primary_color = colors[0] if colors else (255, 0, 0)
            await self.send_wled_command(
                on=True,
                brightness=self.brightness,
                color_primary=primary_color,
            )

        # Advance the wave
        self.color_offset = (self.color_offset + (current_speed / 100.0)) % 1.0
        
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
                "default": 0.03,
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
                "enum": ["speed", "wavelength", "both"],
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
    
    def reload_config(self) -> None:
        """Reload configuration from self.config dictionary."""
        super().reload_config()
        
        # Reload effect-specific config
        self.wave_speed = self.config.get("wave_speed", 1.0)
        self.wave_length = self.config.get("wave_length", 60)
        self.update_interval = self.config.get("update_interval", 0.03)
        self.state_entity = self.config.get("state_entity")
        self.state_attribute = self.config.get("state_attribute")
        self.state_controls = self.config.get("state_controls", "speed")
        self.state_min = self.config.get("state_min", 0.0)
        self.state_max = self.config.get("state_max", 100.0)
