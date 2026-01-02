"""Breathe/Pulse effect for WLED."""
from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING, Any

from ..coordinator import StateSourceCoordinator
from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

if TYPE_CHECKING:
    from wled import WLED

    from homeassistant.core import HomeAssistant


@register_effect
class BreatheEffect(WLEDEffectBase):
    """Breathe/pulse effect with smooth sine wave brightness modulation.
    
    Creates a calming breathing or pulsing pattern. Can be triggered by events
    for notifications/alerts or run continuously for ambient lighting.
    
    Context-aware features:
    - Pulse rate controlled by state (slow calming to fast urgent)
    - Intensity controlled by state (subtle to bright)
    - Color can change based on notification type
    - Trigger-based: pulse N times on events
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
    ) -> None:
        """Initialize breathe effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
        """
        super().__init__(hass, wled_client, config)
        
        # Effect-specific configuration
        self.color: tuple[int, int, int] = self._parse_color(
            config.get("color", "0,100,255")
        )
        self.pulse_rate: float = config.get("pulse_rate", 1.0)  # Cycles per second
        self.min_brightness: int = config.get("min_brightness", 10)
        self.max_brightness: int = config.get("max_brightness", 255)
        self.easing: str = config.get("easing", "sine")  # sine, linear, ease_in_out
        
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
        """Render breathe animation."""
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

        # Calculate brightness using easing function
        eased_value = self._apply_easing(self.phase)
        
        # Map to brightness range
        current_brightness = int(
            current_min_brightness + 
            (current_max_brightness - current_min_brightness) * eased_value
        )

        # Send to WLED
        await self.send_wled_command(
            on=True,
            brightness=current_brightness,
            color_primary=self.color,
        )
        
        # Advance phase based on rate
        # Time step is ~0.05 seconds, so phase increment = rate * 0.05
        phase_increment = current_rate * 0.05
        self.phase = (self.phase + phase_increment) % 1.0
        
        # Control update rate
        await asyncio.sleep(0.05)

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
