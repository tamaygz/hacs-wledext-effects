"""Meter/Gauge effect for WLED."""
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
class MeterEffect(WLEDEffectBase):
    """Meter/gauge effect that displays a value as a fill bar.
    
    Visualizes numeric values (CPU, battery, temperature, progress) as
    a filling bar with configurable colors based on thresholds.
    
    Context-aware features:
    - Fill level directly from state value
    - Color changes based on threshold ranges (green/yellow/red)
    - Multiple fill modes (bottom-up, centered, bidirectional)
    - Smooth transitions with data mapping
    - Can flash/pulse on threshold crossing
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
    ) -> None:
        """Initialize meter effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
        """
        super().__init__(hass, wled_client, config)
        
        # Effect-specific configuration
        self.fill_mode: str = config.get("fill_mode", "bottom_up")  # bottom_up, center_out, bidirectional
        self.default_level: float = config.get("default_level", 50.0)  # Used if no state
        
        # Color thresholds
        self.color_low: tuple[int, int, int] = self._parse_color(
            config.get("color_low", "0,255,0")  # Green
        )
        self.color_medium: tuple[int, int, int] = self._parse_color(
            config.get("color_medium", "255,255,0")  # Yellow
        )
        self.color_high: tuple[int, int, int] = self._parse_color(
            config.get("color_high", "255,0,0")  # Red
        )
        self.threshold_medium: float = config.get("threshold_medium", 50.0)
        self.threshold_high: float = config.get("threshold_high", 80.0)
        
        # Visual options
        self.show_peak: bool = config.get("show_peak", False)
        self.background_color: tuple[int, int, int] = self._parse_color(
            config.get("background_color", "10,10,10")
        )
        
        # State-reactive configuration (optional)
        self.state_entity: str | None = config.get("state_entity")
        self.state_attribute: str | None = config.get("state_attribute")
        self.state_min: float = config.get("state_min", 0.0)
        self.state_max: float = config.get("state_max", 100.0)
        
        # Animation state
        self.current_level: float = self.default_level
        self.peak_level: float = 0.0
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
        """Get state value as percentage (0.0 to 100.0)."""
        if not self.state_coordinator:
            return self.default_level
        
        raw_value = self.state_coordinator.get_numeric_value(
            self.state_min, self.state_max
        )
        
        # Normalize to 0-100 percentage
        value_range = self.state_max - self.state_min
        if value_range <= 0:
            return self.default_level
        
        percentage = ((raw_value - self.state_min) / value_range) * 100.0
        return max(0.0, min(100.0, percentage))

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

    def _get_color_for_level(self, level: float) -> tuple[int, int, int]:
        """Get color based on level and thresholds.

        Args:
            level: Level percentage (0-100)

        Returns:
            RGB color tuple
        """
        if level < self.threshold_medium:
            # Low range - green
            return self.color_low
        elif level < self.threshold_high:
            # Medium range - interpolate between green and yellow
            t = (level - self.threshold_medium) / (self.threshold_high - self.threshold_medium)
            return self.interpolate_color(self.color_medium, self.color_medium, t)
        else:
            # High range - red
            return self.color_high

    async def run_effect(self) -> None:
        """Render meter visualization."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        # Get current level from state
        target_level = self._get_state_value()
        
        # Smooth transition to target level
        self.current_level = self.map_value(
            target_level, 0.0, 100.0, 0.0, 100.0, smooth=True
        )
        
        # Update peak if needed
        if self.show_peak and self.current_level > self.peak_level:
            self.peak_level = self.current_level
        
        # Calculate LED count and fill position
        led_count = (self.stop_led - self.start_led) + 1
        fill_leds = int((self.current_level / 100.0) * led_count)
        
        # Generate colors based on fill mode
        colors: list[tuple[int, int, int]] = []
        
        if self.fill_mode == "bottom_up":
            # Fill from start to current level
            for i in range(led_count):
                if i < fill_leds:
                    # Calculate level for this LED for gradient
                    led_level = ((i + 1) / led_count) * 100.0
                    colors.append(self._get_color_for_level(led_level))
                else:
                    colors.append(self.background_color)
                    
        elif self.fill_mode == "center_out":
            # Fill from center outward
            center = led_count // 2
            half_fill = fill_leds // 2
            for i in range(led_count):
                distance_from_center = abs(i - center)
                if distance_from_center <= half_fill:
                    led_level = (1.0 - distance_from_center / center) * self.current_level
                    colors.append(self._get_color_for_level(led_level))
                else:
                    colors.append(self.background_color)
                    
        elif self.fill_mode == "bidirectional":
            # Split display - left and right from center
            center = led_count // 2
            for i in range(led_count):
                if i < center:
                    # Left side
                    led_level = ((center - i) / center) * self.current_level
                    if (center - i) <= fill_leds // 2:
                        colors.append(self._get_color_for_level(led_level))
                    else:
                        colors.append(self.background_color)
                else:
                    # Right side
                    led_level = ((i - center) / center) * self.current_level
                    if (i - center) <= fill_leds // 2:
                        colors.append(self._get_color_for_level(led_level))
                    else:
                        colors.append(self.background_color)
        
        # Add peak indicator if enabled
        if self.show_peak and self.peak_level > 0:
            peak_led = int((self.peak_level / 100.0) * led_count)
            if peak_led < len(colors):
                colors[peak_led] = (255, 255, 255)  # White peak marker
        
        # Apply reverse direction if configured
        colors = self.apply_reverse(colors)

        # Send primary color as average/representative color
        primary_color = self._get_color_for_level(self.current_level)
        await self.send_wled_command(
            on=True,
            brightness=self.brightness,
            color_primary=primary_color,
        )
        
        # Control update rate
        await asyncio.sleep(0.05)

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for meter effect.

        Returns:
            JSON schema dict
        """
        schema = super().config_schema()
        
        # Add effect-specific fields
        schema["properties"].update({
            "fill_mode": {
                "type": "string",
                "description": "How the meter fills",
                "enum": ["bottom_up", "center_out", "bidirectional"],
                "default": "bottom_up",
            },
            "default_level": {
                "type": "number",
                "description": "Default level when no state (0-100)",
                "minimum": 0.0,
                "maximum": 100.0,
                "default": 50.0,
            },
            "color_low": {
                "type": "string",
                "description": "Color for low values (R,G,B)",
                "default": "0,255,0",
            },
            "color_medium": {
                "type": "string",
                "description": "Color for medium values (R,G,B)",
                "default": "255,255,0",
            },
            "color_high": {
                "type": "string",
                "description": "Color for high values (R,G,B)",
                "default": "255,0,0",
            },
            "threshold_medium": {
                "type": "number",
                "description": "Threshold for medium color (0-100)",
                "minimum": 0.0,
                "maximum": 100.0,
                "default": 50.0,
            },
            "threshold_high": {
                "type": "number",
                "description": "Threshold for high color (0-100)",
                "minimum": 0.0,
                "maximum": 100.0,
                "default": 80.0,
            },
            "show_peak": {
                "type": "boolean",
                "description": "Show peak level indicator",
                "default": False,
            },
            "background_color": {
                "type": "string",
                "description": "Background color for unfilled area (R,G,B)",
                "default": "10,10,10",
            },
            "state_entity": {
                "type": "string",
                "description": "Entity ID to visualize",
            },
            "state_attribute": {
                "type": "string",
                "description": "Optional: Attribute to monitor",
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
