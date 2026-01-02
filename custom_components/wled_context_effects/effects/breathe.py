"""Breathe/Pulse effect for WLED."""
from __future__ import annotations

import asyncio
import logging
import math
from typing import TYPE_CHECKING, Any

from ..coordinator import StateSourceCoordinator
from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

if TYPE_CHECKING:
    from wled import WLED

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@register_effect
class BreatheEffect(WLEDEffectBase):
    """Breathe/pulse effect with traveling wave patterns.
    
    Creates sophisticated breathing patterns that travel across the LED strip,
    showcasing the individual addressability with wave effects, gradients, and
    ripple patterns.
    
    Uses per-LED control for traveling waves, gradient pulses, and ripple effects.
    
    Context-aware features:
    - Pulse rate controlled by state (slow calming to fast urgent)
    - Intensity controlled by state (subtle to bright)
    - Wave patterns (traveling, ripple, gradient, center-out)
    - Color can change based on notification type
    - Trigger-based: pulse N times on events
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
        json_client=None,
    ) -> None:
        """Initialize breathe effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
            json_client: Optional WLEDJsonAPI client for per-LED control
        """
        super().__init__(hass, wled_client, config, json_client)
        
        # Effect-specific configuration
        self.color: tuple[int, int, int] = self._parse_color(
            config.get("color", "0,100,255")
        )
        self.pulse_rate: float = config.get("pulse_rate", 1.0)  # Cycles per second
        self.min_brightness: int = config.get("min_brightness", 10)
        self.max_brightness: int = config.get("max_brightness", 255)
        self.easing: str = config.get("easing", "sine")  # sine, linear, ease_in_out
        self.wave_pattern: str = config.get("wave_pattern", "traveling")  # traveling, ripple, gradient, center_out
        
        # State-reactive configuration (optional)
        self.state_entity: str | None = config.get("state_entity")
        self.state_attribute: str | None = config.get("state_attribute")
        self.state_controls: str = config.get("state_controls", "rate")  # rate, intensity, both
        self.state_min: float = config.get("state_min", 0.0)
        self.state_max: float = config.get("state_max", 100.0)
        
        # Animation state
        self.phase: float = 0.0  # 0.0 to 1.0 representing one full breath cycle
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
            return (0, 100, 255)  # Default to blue

    def _apply_easing(self, t: float) -> float:
        """Apply easing function to phase value.

        Args:
            t: Phase value (0.0 to 1.0)

        Returns:
            Eased value (0.0 to 1.0)
        """
        if self.easing == "linear":
            # Simple triangle wave
            return 1.0 - abs(2.0 * t - 1.0)
        elif self.easing == "ease_in_out":
            # Smooth ease in/out
            return (math.cos((t * 2.0 - 1.0) * math.pi) + 1.0) / 2.0
        else:  # sine (default)
            # Sine wave (most natural breathing)
            return (math.sin(t * 2.0 * math.pi - math.pi / 2.0) + 1.0) / 2.0

    async def run_effect(self) -> None:
        """Render breathe animation with per-LED wave patterns."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        # Get state value if configured
        state_value = self._get_state_value() if self.state_entity else None
        
        # Determine current pulse rate and intensity based on state
        current_rate = self.pulse_rate
        current_min_brightness = self.min_brightness
        current_max_brightness = self.max_brightness
        
        if state_value is not None:
            if self.state_controls in ["rate", "both"]:
                # Map state to pulse rate (0.1 to 10.0 Hz)
                current_rate = self.map_value(
                    state_value, 0.0, 1.0, 0.1, 10.0, smooth=True
                )
            if self.state_controls in ["intensity", "both"]:
                # Map state to brightness range
                current_max_brightness = int(self.map_value(
                    state_value, 0.0, 1.0, 50.0, 255.0, smooth=True
                ))

        # Calculate eased value for animation
        eased_value = self._apply_easing(self.phase)
        
        # Generate per-LED colors with wave pattern
        led_colors = self._generate_wave_pattern(
            eased_value,
            current_min_brightness,
            current_max_brightness,
        )
        
        # Try per-LED control first
        if self.json_client and led_colors:
            try:
                await self.set_individual_leds(led_colors)
                # Advance phase based on rate
                phase_increment = current_rate * 0.05
                self.phase = (self.phase + phase_increment) % 1.0
                await asyncio.sleep(0.05)
                return
            except Exception as e:
                _LOGGER.warning("Per-LED control failed, falling back to segment mode: %s", e)
        
        # Fallback to segment-level control
        current_brightness = int(
            current_min_brightness + 
            (current_max_brightness - current_min_brightness) * eased_value
        )
        
        await self.send_wled_command(
            on=True,
            brightness=current_brightness,
            color_primary=self.color,
        )
        
        # Advance phase based on rate
        phase_increment = current_rate * 0.05
        self.phase = (self.phase + phase_increment) % 1.0
        
        # Control update rate
        await asyncio.sleep(0.05)
    
    def _generate_wave_pattern(
        self,
        intensity: float,
        min_brightness: int,
        max_brightness: int,
    ) -> list[tuple[int, int, int]]:
        """Generate per-LED wave breathing pattern.
        
        Args:
            intensity: Current breath intensity (0.0 to 1.0)
            min_brightness: Minimum brightness value
            max_brightness: Maximum brightness value
            
        Returns:
            List of RGB tuples for each LED
        """
        if not self.led_count:
            return []
        
        colors = []
        
        if self.wave_pattern == "traveling":
            # Traveling wave across strip
            for i in range(self.led_count):
                # Create traveling wave
                wave_pos = (i / self.led_count + self.phase) % 1.0
                led_intensity = self._apply_easing(wave_pos)
                brightness = int(min_brightness + (max_brightness - min_brightness) * led_intensity)
                # Apply brightness to color
                color = tuple(int(c * brightness / 255) for c in self.color)
                colors.append(color)
        
        elif self.wave_pattern == "ripple":
            # Ripple from center outward
            center = self.led_count / 2
            for i in range(self.led_count):
                # Distance from center
                distance = abs(i - center) / center
                # Create ripple
                wave_pos = (distance + self.phase) % 1.0
                led_intensity = self._apply_easing(wave_pos)
                brightness = int(min_brightness + (max_brightness - min_brightness) * led_intensity)
                color = tuple(int(c * brightness / 255) for c in self.color)
                colors.append(color)
        
        elif self.wave_pattern == "gradient":
            # Gradient breathing that shifts
            for i in range(self.led_count):
                # Gradient position shifts with phase
                gradient_pos = ((i / self.led_count) + self.phase * 0.5) % 1.0
                # Apply overall intensity
                led_intensity = gradient_pos * intensity
                brightness = int(min_brightness + (max_brightness - min_brightness) * led_intensity)
                color = tuple(int(c * brightness / 255) for c in self.color)
                colors.append(color)
        
        elif self.wave_pattern == "center_out":
            # Breathe from center outward
            center = self.led_count / 2
            for i in range(self.led_count):
                distance = abs(i - center) / center
                # Sync with phase but attenuate by distance
                led_intensity = intensity * (1.0 - distance * 0.5)
                brightness = int(min_brightness + (max_brightness - min_brightness) * led_intensity)
                color = tuple(int(c * brightness / 255) for c in self.color)
                colors.append(color)
        
        return colors

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for breathe effect.

        Returns:
            JSON schema dict
        """
        schema = super().config_schema()
        
        # Add effect-specific fields
        schema["properties"].update({
            "color": {
                "type": "string",
                "description": "LED color (R,G,B format)",
                "default": "0,100,255",
            },
            "pulse_rate": {
                "type": "number",
                "description": "Breathing rate in cycles per second",
                "minimum": 0.1,
                "maximum": 10.0,
                "default": 1.0,
            },
            "min_brightness": {
                "type": "integer",
                "description": "Minimum brightness (0-255)",
                "minimum": 0,
                "maximum": 255,
                "default": 10,
            },
            "max_brightness": {
                "type": "integer",
                "description": "Maximum brightness (0-255)",
                "minimum": 0,
                "maximum": 255,
                "default": 255,
            },
            "easing": {
                "type": "string",
                "description": "Easing function for breathing pattern",
                "enum": ["sine", "linear", "ease_in_out"],
                "default": "sine",
            },
            "wave_pattern": {
                "type": "string",
                "description": "Wave pattern mode for per-LED control",
                "enum": ["traveling", "ripple", "gradient", "center_out"],
                "default": "traveling",
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
                "enum": ["rate", "intensity", "both"],
                "default": "rate",
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
