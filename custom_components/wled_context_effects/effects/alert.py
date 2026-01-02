"""Alert/Notification effect for WLED."""
from __future__ import annotations

import asyncio
import logging
import random
import time
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..coordinator import StateSourceCoordinator
from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

if TYPE_CHECKING:
    from wled import WLED

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class Severity(Enum):
    """Alert severity levels."""
    
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


# Default severity configurations
SEVERITY_DEFAULTS = {
    Severity.DEBUG: {
        "color": (50, 50, 150),  # Dim blue
        "flash_rate": 0.5,  # 0.5 Hz
        "pattern": "blink",
    },
    Severity.INFO: {
        "color": (0, 150, 255),  # Bright blue/cyan
        "flash_rate": 1.0,  # 1 Hz
        "pattern": "pulse",
    },
    Severity.WARNING: {
        "color": (255, 200, 0),  # Yellow/amber
        "flash_rate": 2.0,  # 2 Hz
        "pattern": "double_pulse",
    },
    Severity.ALERT: {
        "color": (255, 100, 0),  # Orange
        "flash_rate": 3.0,  # 3 Hz
        "pattern": "triple_pulse",
    },
    Severity.CRITICAL: {
        "color": (255, 0, 0),  # Red
        "flash_rate": 6.0,  # 6 Hz
        "pattern": "strobe",
    },
}


@register_effect
class AlertEffect(WLEDEffectBase):
    """Alert/notification effect with severity levels and patterns.
    
    Highly customizable notification effect supporting multiple severity levels,
    flash patterns, and attention-grabbing techniques. Perfect for alerts,
    warnings, and status notifications.
    
    Uses per-LED control for sparkle_burst pattern and targeted area effects.
    
    Context-aware features:
    - Auto-severity from state value (thresholds)
    - Acknowledgment support (stops when acknowledged)
    - Auto-escalation (increases severity over time)
    - Multiple flash patterns (blink, pulse, strobe, sparkle burst)
    - Customizable per-severity colors and rates
    - Zone support for multi-alert display
    - Duration limit with auto-stop
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
        json_client=None,
    ) -> None:
        """Initialize alert effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance
            config: Effect configuration
            json_client: Optional JSON API client for per-LED control
        """
        super().__init__(hass, wled_client, config, json_client)
        
        # Severity configuration
        severity_str = config.get("severity", "info")
        self.severity: Severity = Severity(severity_str) if severity_str != "auto" else None
        self.auto_severity: bool = severity_str == "auto"
        
        # Pattern configuration
        self.pattern: str = config.get("pattern", "auto")  # auto uses severity default
        self.flash_rate: float = config.get("flash_rate", 0.0)  # 0 = use default
        self.duty_cycle: float = config.get("duty_cycle", 0.5)  # On-time percentage
        
        # Color configuration
        color_str = config.get("color", "auto")
        self.custom_color: tuple[int, int, int] | None = (
            self._parse_color(color_str) if color_str != "auto" else None
        )
        self.secondary_color: tuple[int, int, int] | None = (
            self._parse_color(config.get("secondary_color", "255,255,255"))
            if config.get("secondary_color") else None
        )
        
        # Sparkle burst configuration
        self.sparkle_count: int = config.get("sparkle_count", 50)
        self.sparkle_decay: float = config.get("sparkle_decay", 0.85)
        
        # Area configuration
        self.affected_area: str = config.get("affected_area", "full")  # full/center/edges/random
        
        # Advanced features
        self.escalate_after: float = config.get("escalate_after", 0.0)  # Seconds
        self.max_duration: float = config.get("max_duration", 0.0)  # Seconds, 0=infinite
        self.acknowledge_entity: str | None = config.get("acknowledge_entity")
        
        # Auto-severity from state
        self.state_entity: str | None = config.get("state_entity")
        self.state_attribute: str | None = config.get("state_attribute")
        self.severity_thresholds: dict[str, float] = config.get("severity_thresholds", {
            "debug": 10.0,
            "info": 30.0,
            "warning": 60.0,
            "alert": 85.0,
            # Above alert = critical
        })
        
        # Animation state
        self.phase: float = 0.0
        self.start_time: float = time.time()
        self.last_escalation: float = time.time()
        self.current_severity: Severity = self.severity or Severity.INFO
        self.sparkle_brightness: list[float] = []
        self.acknowledged: bool = False
        
        # Coordinators
        self.state_coordinator: StateSourceCoordinator | None = None
        self.ack_coordinator: StateSourceCoordinator | None = None

    async def setup(self) -> bool:
        """Setup effect with optional state coordinators."""
        if not await super().setup():
            return False
        
        # Initialize sparkle tracking
        led_count = (self.stop_led - self.start_led) + 1
        self.sparkle_brightness = [0.0] * led_count
        
        # Create state coordinator for auto-severity
        if self.state_entity:
            self.state_coordinator = StateSourceCoordinator(
                self.hass,
                self.state_entity,
                self.state_attribute,
            )
            await self.state_coordinator.async_setup()
            await self.state_coordinator.async_config_entry_first_refresh()
        
        # Create acknowledgment coordinator
        if self.acknowledge_entity:
            self.ack_coordinator = StateSourceCoordinator(
                self.hass,
                self.acknowledge_entity,
            )
            await self.ack_coordinator.async_setup()
            await self.ack_coordinator.async_config_entry_first_refresh()
        
        return True

    async def stop(self) -> None:
        """Stop effect and cleanup coordinators."""
        await super().stop()
        
        if self.state_coordinator:
            await self.state_coordinator.async_shutdown()
        if self.ack_coordinator:
            await self.ack_coordinator.async_shutdown()

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

    def _get_severity_from_state(self) -> Severity:
        """Determine severity from state value.

        Returns:
            Severity level based on thresholds
        """
        if not self.state_coordinator:
            return Severity.INFO
        
        # Get state value as percentage
        try:
            value = float(self.state_coordinator.state.state)
        except (ValueError, AttributeError):
            return Severity.INFO
        
        # Map to severity based on thresholds
        if value < self.severity_thresholds.get("debug", 10.0):
            return Severity.DEBUG
        elif value < self.severity_thresholds.get("info", 30.0):
            return Severity.INFO
        elif value < self.severity_thresholds.get("warning", 60.0):
            return Severity.WARNING
        elif value < self.severity_thresholds.get("alert", 85.0):
            return Severity.ALERT
        else:
            return Severity.CRITICAL

    def _check_acknowledgment(self) -> bool:
        """Check if alert has been acknowledged.

        Returns:
            True if acknowledged
        """
        if not self.ack_coordinator:
            return False
        
        try:
            state = self.ack_coordinator.state.state
            return state.lower() in ["on", "true", "1", "acknowledged"]
        except AttributeError:
            return False

    def _escalate_severity(self) -> None:
        """Escalate to next severity level."""
        severity_order = [Severity.DEBUG, Severity.INFO, Severity.WARNING, Severity.ALERT, Severity.CRITICAL]
        current_idx = severity_order.index(self.current_severity)
        if current_idx < len(severity_order) - 1:
            self.current_severity = severity_order[current_idx + 1]
            self.last_escalation = time.time()

    def _get_current_config(self) -> dict[str, Any]:
        """Get current color, rate, and pattern based on severity.

        Returns:
            Dict with color, flash_rate, pattern
        """
        defaults = SEVERITY_DEFAULTS[self.current_severity]
        
        return {
            "color": self.custom_color or defaults["color"],
            "flash_rate": self.flash_rate or defaults["flash_rate"],
            "pattern": self.pattern if self.pattern != "auto" else defaults["pattern"],
        }

    def _get_affected_leds(self, led_count: int) -> list[int]:
        """Get list of LED indices to affect based on area setting.

        Args:
            led_count: Total LED count

        Returns:
            List of LED indices
        """
        if self.affected_area == "full":
            return list(range(led_count))
        elif self.affected_area == "center":
            quarter = led_count // 4
            return list(range(quarter, 3 * quarter))
        elif self.affected_area == "edges":
            quarter = led_count // 4
            return list(range(quarter)) + list(range(3 * quarter, led_count))
        elif self.affected_area == "random":
            count = led_count // 2
            return random.sample(range(led_count), count)
        else:
            return list(range(led_count))

    def _generate_pattern(self, config: dict[str, Any], led_count: int) -> list[tuple[int, int, int]]:
        """Generate LED colors for current pattern.

        Args:
            config: Current configuration (color, flash_rate, pattern)
            led_count: Number of LEDs

        Returns:
            List of RGB colors
        """
        pattern = config["pattern"]
        color = config["color"]
        flash_rate = config["flash_rate"]
        
        # Calculate pattern phase
        cycle_time = 1.0 / flash_rate if flash_rate > 0 else 1.0
        phase_in_cycle = (self.phase % cycle_time) / cycle_time
        
        affected_leds = self._get_affected_leds(led_count)
        colors: list[tuple[int, int, int]] = [(0, 0, 0)] * led_count
        
        if pattern == "steady":
            # Solid color
            for i in affected_leds:
                colors[i] = color
                
        elif pattern == "blink":
            # Simple on/off
            if phase_in_cycle < self.duty_cycle:
                for i in affected_leds:
                    colors[i] = color
                    
        elif pattern == "pulse":
            # Smooth sine wave
            import math
            brightness = (math.sin(phase_in_cycle * 2 * math.pi - math.pi / 2) + 1) / 2
            pulsed_color = tuple(int(c * brightness) for c in color)
            for i in affected_leds:
                colors[i] = pulsed_color
                
        elif pattern == "double_pulse":
            # Two quick flashes per cycle
            if phase_in_cycle < 0.15 or (0.3 < phase_in_cycle < 0.45):
                for i in affected_leds:
                    colors[i] = color
                    
        elif pattern == "triple_pulse":
            # Three quick flashes per cycle
            if (phase_in_cycle < 0.1 or 
                (0.2 < phase_in_cycle < 0.3) or 
                (0.4 < phase_in_cycle < 0.5)):
                for i in affected_leds:
                    colors[i] = color
                    
        elif pattern == "strobe":
            # Very brief bright flash
            if phase_in_cycle < 0.1:
                for i in affected_leds:
                    colors[i] = color
                # Add white flash for critical
                if self.current_severity == Severity.CRITICAL and self.secondary_color:
                    if phase_in_cycle < 0.05:
                        for i in affected_leds:
                            colors[i] = self.secondary_color
                            
        elif pattern == "sparkle_burst":
            # Random sparkle explosion
            # Add new sparkles
            if phase_in_cycle < 0.2:
                for _ in range(self.sparkle_count // 10):
                    led_idx = random.choice(affected_leds)
                    self.sparkle_brightness[led_idx] = 1.0
            
            # Decay all sparkles
            for i in range(led_count):
                if self.sparkle_brightness[i] > 0:
                    self.sparkle_brightness[i] *= self.sparkle_decay
                    if self.sparkle_brightness[i] < 0.01:
                        self.sparkle_brightness[i] = 0.0
                    
                    if i in affected_leds:
                        brightness = self.sparkle_brightness[i]
                        colors[i] = tuple(int(c * brightness) for c in color)
        
        return colors

    async def run_effect(self) -> None:
        """Render alert animation."""
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            return

        # Check acknowledgment
        if self._check_acknowledgment():
            self.acknowledged = True
            # Stop effect
            await self.send_wled_command(on=False)
            return

        # Check max duration
        if self.max_duration > 0:
            elapsed = time.time() - self.start_time
            if elapsed > self.max_duration:
                # Auto-stop
                await self.send_wled_command(on=False)
                return

        # Update severity from state if auto
        if self.auto_severity and self.state_coordinator:
            self.current_severity = self._get_severity_from_state()
        
        # Check for escalation
        if self.escalate_after > 0 and not self.acknowledged:
            if time.time() - self.last_escalation > self.escalate_after:
                self._escalate_severity()

        # Get current configuration
        config = self._get_current_config()
        
        # Generate pattern
        led_count = (self.stop_led - self.start_led) + 1
        colors = self._generate_pattern(config, led_count)
        
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
                    color_primary=config["color"],
                )
        else:
            # No JSON client - use basic command
            await self.send_wled_command(
                on=True,
                brightness=self.brightness,
                color_primary=config["color"],
            )
        
        # Advance phase
        self.phase += 0.05  # 50ms time step
        
        # Control update rate
        await asyncio.sleep(0.05)

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for alert effect.

        Returns:
            JSON schema dict
        """
        schema = super().config_schema()
        
        # Add effect-specific fields
        schema["properties"].update({
            "severity": {
                "type": "string",
                "description": "Alert severity level or 'auto'",
                "enum": ["debug", "info", "warning", "alert", "critical", "auto"],
                "default": "info",
            },
            "pattern": {
                "type": "string",
                "description": "Flash pattern type or 'auto' for severity default",
                "enum": ["auto", "steady", "blink", "pulse", "double_pulse", "triple_pulse", "strobe", "sparkle_burst"],
                "default": "auto",
            },
            "flash_rate": {
                "type": "number",
                "description": "Flash rate in Hz (0 = use severity default)",
                "minimum": 0.0,
                "maximum": 10.0,
                "default": 0.0,
            },
            "duty_cycle": {
                "type": "number",
                "description": "On-time percentage for blink pattern",
                "minimum": 0.1,
                "maximum": 0.9,
                "default": 0.5,
            },
            "color": {
                "type": "string",
                "description": "Alert color (R,G,B) or 'auto' for severity default",
                "default": "auto",
            },
            "secondary_color": {
                "type": "string",
                "description": "Secondary color for alternating patterns (R,G,B)",
                "default": "255,255,255",
            },
            "sparkle_count": {
                "type": "integer",
                "description": "Number of sparkles for sparkle_burst pattern",
                "minimum": 10,
                "maximum": 200,
                "default": 50,
            },
            "sparkle_decay": {
                "type": "number",
                "description": "Sparkle fade rate (lower = faster fade)",
                "minimum": 0.5,
                "maximum": 0.98,
                "default": 0.85,
            },
            "affected_area": {
                "type": "string",
                "description": "Which LEDs to affect",
                "enum": ["full", "center", "edges", "random"],
                "default": "full",
            },
            "escalate_after": {
                "type": "number",
                "description": "Seconds before escalating severity (0 = disabled)",
                "minimum": 0.0,
                "default": 0.0,
            },
            "max_duration": {
                "type": "number",
                "description": "Auto-stop after N seconds (0 = infinite)",
                "minimum": 0.0,
                "default": 0.0,
            },
            "acknowledge_entity": {
                "type": "string",
                "description": "Entity to monitor for acknowledgment (stops when 'on')",
            },
            "state_entity": {
                "type": "string",
                "description": "Entity for auto-severity based on value",
            },
            "state_attribute": {
                "type": "string",
                "description": "Optional: Attribute to monitor",
            },
            "severity_thresholds": {
                "type": "object",
                "description": "State value thresholds for severity levels",
                "properties": {
                    "debug": {"type": "number", "default": 10.0},
                    "info": {"type": "number", "default": 30.0},
                    "warning": {"type": "number", "default": 60.0},
                    "alert": {"type": "number", "default": 85.0},
                },
                "default": {
                    "debug": 10.0,
                    "info": 30.0,
                    "warning": 60.0,
                    "alert": 85.0,
                },
            },
        })
        
        return schema
