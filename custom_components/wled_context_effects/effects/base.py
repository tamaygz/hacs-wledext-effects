"""Base classes and protocols for WLED effects."""
from __future__ import annotations

import asyncio
import logging
from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from wled import WLED

from ..const import (
    BLEND_MODE_AVERAGE,
    DEFAULT_BLEND_MODE,
    DEFAULT_BRIGHTNESS,
    DEFAULT_FREEZE_ON_MANUAL,
    DEFAULT_REVERSE_DIRECTION,
    DEFAULT_SEGMENT_ID,
    DEFAULT_TRANSITION_MODE,
    DEFAULT_ZONE_COUNT,
    TRANSITION_MODE_SMOOTH,
)
from ..data_mapper import DataMapper, MultiInputBlender, ValueSmoother
from ..errors import EffectExecutionError
from ..trigger_manager import TriggerConfig, TriggerManager
from ..wled_json_api import WLEDJsonApiClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@runtime_checkable
class EffectProtocol(Protocol):
    """Protocol defining the effect interface."""

    async def start(self) -> None:
        """Start the effect (continuous mode)."""
        ...

    async def stop(self) -> None:
        """Stop the effect."""
        ...

    async def run_once(self) -> None:
        """Execute effect once."""
        ...

    @property
    def running(self) -> bool:
        """Return if effect is currently running."""
        ...

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return JSON schema for effect configuration."""
        ...

    def get_effect_name(self) -> str:
        """Return human-readable effect name."""
        ...


class WLEDEffectBase:
    """Base class for WLED effects using python-wled library.
    
    This class provides common functionality for all WLED effects including:
    - Lifecycle management (start/stop/run_once)
    - WLED communication via python-wled
    - Per-LED control via JSON API
    - Auto-detection of LED ranges
    - Error handling and logging
    - Configuration management
    
    Subclasses should implement the run_effect() method with their custom logic.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
        json_client: WLEDJsonApiClient | None = None,
    ) -> None:
        """Initialize effect.

        Args:
            hass: Home Assistant instance
            wled_client: WLED client instance from python-wled library
            config: Effect configuration dictionary
            json_client: Optional JSON API client for per-LED control
        """
        self.hass = hass
        self.wled = wled_client
        self.json_client = json_client
        self.config = config
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_error: str | None = None
        self._command_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._start_time: datetime | None = None

        # Extract common config
        self.segment_id: int = config.get("segment_id", DEFAULT_SEGMENT_ID)
        self.start_led: int | None = config.get("start_led")
        self.stop_led: int | None = config.get("stop_led")
        self.brightness: int = config.get("brightness", DEFAULT_BRIGHTNESS)

        # Context-aware features
        self.reverse_direction: bool = config.get("reverse_direction", DEFAULT_REVERSE_DIRECTION)
        self.freeze_on_manual: bool = config.get("freeze_on_manual", DEFAULT_FREEZE_ON_MANUAL)
        self.blend_mode: str = config.get("blend_mode", DEFAULT_BLEND_MODE)
        self.transition_mode: str = config.get("transition_mode", DEFAULT_TRANSITION_MODE)
        self.zone_count: int = config.get("zone_count", DEFAULT_ZONE_COUNT)
        
        # Reactive inputs - list of entity IDs to monitor
        self.reactive_inputs: list[str] = config.get("reactive_inputs", [])
        
        # Data mapping and smoothing (initialize eagerly for consistency)
        self.data_mapper = DataMapper()
        self.value_smoother: ValueSmoother | None = None
        if self.transition_mode == TRANSITION_MODE_SMOOTH:
            self.value_smoother = ValueSmoother(alpha=0.3)
        
        # Trigger management
        self.trigger_manager: TriggerManager | None = None
        if config.get("trigger_config"):
            self.trigger_manager = TriggerManager(hass)
        
        # Multi-input blending
        self.input_blender = MultiInputBlender()

        _LOGGER.debug(
            "Initialized effect %s with config: %s (reverse=%s, zones=%d, reactive_inputs=%d, json_api=%s)",
            self.__class__.__name__,
            config,
            self.reverse_direction,
            self.zone_count,
            len(self.reactive_inputs),
            json_client is not None,
        )

    async def setup(self) -> bool:
        """Setup effect (called once after init).

        Returns:
            True if setup successful
        """
        try:
            # Auto-detect LED range if not specified
            if self.start_led is None or self.stop_led is None:
                await self._auto_detect_range()

            # Setup trigger manager if configured
            if self.trigger_manager:
                await self.trigger_manager.setup()

            _LOGGER.info(
                "Effect %s setup complete. LED range: %d-%d, Segment: %d",
                self.__class__.__name__,
                self.start_led,
                self.stop_led,
                self.segment_id,
            )
            return True
        except Exception as err:
            _LOGGER.error("Failed to setup effect: %s", err)
            return False

    async def start(self) -> None:
        """Start effect in continuous mode."""
        if self._running:
            _LOGGER.warning("Effect %s is already running", self.__class__.__name__)
            return

        _LOGGER.info("Starting effect %s", self.__class__.__name__)
        self._running = True
        self._start_time = datetime.now()
        self._last_error = None
        self._task = self.hass.async_create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the effect."""
        if not self._running:
            _LOGGER.debug("Effect %s is not running", self.__class__.__name__)
            return

        _LOGGER.info("Stopping effect %s", self.__class__.__name__)
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # Cleanup trigger manager
        if self.trigger_manager:
            await self.trigger_manager.shutdown()

        self._start_time = None

    async def run_once(self) -> None:
        """Run effect once."""
        _LOGGER.debug("Running effect %s once", self.__class__.__name__)
        try:
            await self.run_effect()
        except Exception as err:
            _LOGGER.error("Error running effect once: %s", err)
            self._last_error = str(err)
            raise EffectExecutionError(f"Failed to run effect: {err}") from err

    async def _run_loop(self) -> None:
        """Main effect loop (continuous mode)."""
        _LOGGER.debug("Starting effect loop for %s", self.__class__.__name__)

        while self._running:
            try:
                await self.run_effect()
                self._success_count += 1
            except asyncio.CancelledError:
                _LOGGER.debug("Effect loop cancelled")
                break
            except Exception as err:
                _LOGGER.error("Error in effect loop: %s", err)
                self._last_error = str(err)
                self._failure_count += 1

                # Continue running despite errors, but add a delay
                await asyncio.sleep(1)

    @abstractmethod
    async def run_effect(self) -> None:
        """Effect implementation - override in subclass.
        
        This method is called repeatedly in continuous mode or once in run_once mode.
        Implement your effect logic here.
        
        Example:
            async def run_effect(self) -> None:
                # Generate colors
                colors = self._generate_colors()
                
                # Send to WLED
                await self.send_wled_command(
                    color_primary=colors,
                    brightness=self.brightness
                )
                
                # Wait before next update
                await asyncio.sleep(0.1)
        """
        raise NotImplementedError

    async def send_wled_command(self, **kwargs: Any) -> bool:
        """Send command to WLED device.

        Args:
            **kwargs: Arguments passed to wled.segment()

        Returns:
            True if command successful

        Raises:
            EffectExecutionError: If command fails
        """
        self._command_count += 1

        try:
            # Add segment_id to kwargs if not present
            if "segment_id" not in kwargs:
                kwargs["segment_id"] = self.segment_id

            _LOGGER.debug(
                "Sending WLED command to segment %d: %s",
                self.segment_id,
                kwargs,
            )

            await self.wled.segment(**kwargs)
            self._success_count += 1
            return True

        except Exception as err:
            _LOGGER.error("WLED command failed: %s", err)
            self._last_error = str(err)
            self._failure_count += 1
            raise EffectExecutionError(f"WLED command failed: {err}") from err

    async def set_individual_leds(
        self,
        colors: list[tuple[int, int, int]],
        start_index: int = 0,
    ) -> bool:
        """Set individual LED colors using JSON API.

        This method provides true per-LED control using the WLED JSON API.
        Automatically handles batching for large LED arrays.

        Args:
            colors: List of RGB tuples (one per LED)
            start_index: Starting LED index in segment (default 0)

        Returns:
            True if successful

        Raises:
            EffectExecutionError: If JSON client not available or command fails
        """
        if self.json_client is None:
            raise EffectExecutionError(
                "JSON API client required for per-LED control. "
                "Pass json_client when creating effect."
            )

        self._command_count += 1

        try:
            _LOGGER.debug(
                "Setting %d LEDs via JSON API on segment %d (start index: %d)",
                len(colors),
                self.segment_id,
                start_index,
            )

            await self.json_client.set_individual_leds(
                segment_id=self.segment_id,
                colors=colors,
                start_index=start_index,
            )

            self._success_count += 1
            return True

        except (WLEDConnectionError, OSError, asyncio.TimeoutError) as err:
            _LOGGER.error("Per-LED control connection error: %s", err)
            self._last_error = str(err)
            self._failure_count += 1
            raise EffectExecutionError(f"Per-LED control connection error: {err}") from err
        except (ValueError, TypeError, AttributeError) as err:
            _LOGGER.error("Per-LED control data error: %s", err)
            self._last_error = str(err)
            self._failure_count += 1
            raise EffectExecutionError(f"Per-LED control data error: {err}") from err

    async def set_led(
        self,
        led_index: int,
        color: tuple[int, int, int],
    ) -> bool:
        """Set a single LED color using JSON API.

        Args:
            led_index: LED index within segment (0-based)
            color: RGB color tuple

        Returns:
            True if successful

        Raises:
            EffectExecutionError: If JSON client not available or command fails
        """
        if self.json_client is None:
            raise EffectExecutionError("JSON API client required for per-LED control")

        self._command_count += 1

        try:
            await self.json_client.set_led(
                segment_id=self.segment_id,
                led_index=led_index,
                color=color,
            )

            self._success_count += 1
            return True

        except (WLEDConnectionError, OSError, asyncio.TimeoutError) as err:
            _LOGGER.error("Set LED connection error: %s", err)
            self._last_error = str(err)
            self._failure_count += 1
            raise EffectExecutionError(f"Set LED connection error: {err}") from err
        except (ValueError, TypeError) as err:
            _LOGGER.error("Set LED data error: %s", err)
            self._last_error = str(err)
            self._failure_count += 1
            raise EffectExecutionError(f"Set LED data error: {err}") from err

    async def set_led_range(
        self,
        start: int,
        stop: int,
        color: tuple[int, int, int],
    ) -> bool:
        """Set a range of LEDs to the same color using JSON API.

        Args:
            start: Start LED index (inclusive)
            stop: Stop LED index (inclusive)
            color: RGB color tuple

        Returns:
            True if successful

        Raises:
            EffectExecutionError: If JSON client not available or command fails
        """
        if self.json_client is None:
            raise EffectExecutionError("JSON API client required for per-LED control")

        self._command_count += 1

        try:
            await self.json_client.set_led_range(
                segment_id=self.segment_id,
                start=start,
                stop=stop,
                color=color,
            )

            self._success_count += 1
            return True

        except (WLEDConnectionError, OSError, asyncio.TimeoutError) as err:
            _LOGGER.error("Set LED range connection error: %s", err)
            self._last_error = str(err)
            self._failure_count += 1
            raise EffectExecutionError(f"Set LED range connection error: {err}") from err
        except (ValueError, TypeError) as err:
            _LOGGER.error("Set LED range data error: %s", err)
            self._last_error = str(err)
            self._failure_count += 1
            raise EffectExecutionError(f"Set LED range data error: {err}") from err

    async def clear_individual_leds(self) -> bool:
        """Clear individual LED control and return segment to effect mode.

        Returns:
            True if successful

        Raises:
            EffectExecutionError: If JSON client not available or command fails
        """
        if self.json_client is None:
            _LOGGER.debug("JSON API client not available, skipping clear")
            return True

        try:
            await self.json_client.clear_individual_leds(self.segment_id)
            return True

        except (WLEDConnectionError, OSError, asyncio.TimeoutError) as err:
            _LOGGER.error("Clear individual LEDs connection error: %s", err)
            self._last_error = str(err)
            raise EffectExecutionError(f"Clear individual LEDs connection error: {err}") from err
        except (ValueError, TypeError) as err:
            _LOGGER.error("Clear individual LEDs data error: %s", err)
            self._last_error = str(err)
            raise EffectExecutionError(f"Clear individual LEDs data error: {err}") from err

    async def _auto_detect_range(self) -> None:
        """Auto-detect LED range from device."""
        try:
            _LOGGER.debug("Auto-detecting LED range for WLED device")
            device = await self.wled.update()

            if device and device.info and device.info.leds:
                led_count = device.info.leds.count
                if led_count and led_count > 0:
                    self.start_led = 0
                    self.stop_led = led_count - 1
                    _LOGGER.info(
                        "Auto-detected LED range: 0-%d (%d LEDs)",
                        self.stop_led,
                        led_count,
                    )
                else:
                    _LOGGER.warning("Device reported 0 LEDs, using defaults")
                    self.start_led = 0
                    self.stop_led = 59  # Default fallback
            else:
                _LOGGER.warning("Could not get device info, using defaults")
                self.start_led = 0
                self.stop_led = 59  # Default fallback

        except Exception as err:
            _LOGGER.error("Failed to auto-detect LED range: %s", err)
            # Use sensible defaults
            self.start_led = 0
            self.stop_led = 59

    def apply_reverse(self, led_array: list[Any]) -> list[Any]:
        """Apply reverse direction to LED array.
        
        If reverse_direction is enabled, reverses the order of LEDs.
        This allows effects to run in opposite direction.

        Args:
            led_array: List of LED values (colors, brightness, etc.)

        Returns:
            Reversed or original list based on config
        """
        if self.reverse_direction:
            return list(reversed(led_array))
        return led_array

    def map_to_zone(self, zone_index: int) -> tuple[int, int]:
        """Map zone index to LED range.
        
        Divides the LED strip into zones and returns the LED range for a specific zone.

        Args:
            zone_index: Zone number (0-based)

        Returns:
            Tuple of (start_led, stop_led) for the zone
        """
        if self.start_led is None or self.stop_led is None:
            return (0, 0)

        total_leds = (self.stop_led - self.start_led) + 1
        zone_size = total_leds // self.zone_count
        
        zone_start = self.start_led + (zone_index * zone_size)
        zone_stop = zone_start + zone_size - 1
        
        # Ensure last zone covers remaining LEDs
        if zone_index == self.zone_count - 1:
            zone_stop = self.stop_led

        return (zone_start, zone_stop)

    def map_value(
        self,
        value: float,
        input_min: float,
        input_max: float,
        output_min: float,
        output_max: float,
        smooth: bool = False,
    ) -> float:
        """Map value from input range to output range.

        Args:
            value: Input value
            input_min: Minimum input value
            input_max: Maximum input value
            output_min: Minimum output value
            output_max: Maximum output value
            smooth: Apply smoothing if enabled

        Returns:
            Mapped output value
        """
        # Update mapper ranges
        self.data_mapper.input_min = input_min
        self.data_mapper.input_max = input_max
        self.data_mapper.output_min = output_min
        self.data_mapper.output_max = output_max

        mapped = self.data_mapper.map(value)

        # Apply smoothing if requested and enabled
        if smooth and self.value_smoother:
            mapped = self.value_smoother.smooth(mapped)

        return mapped

    def blend_values(self, values: list[float]) -> float:
        """Blend multiple input values using configured blend mode.

        Args:
            values: List of values to blend

        Returns:
            Blended value
        """
        return self.input_blender.blend(values, self.blend_mode)

    def interpolate_color(
        self,
        color1: tuple[int, int, int],
        color2: tuple[int, int, int],
        position: float,
    ) -> tuple[int, int, int]:
        """Interpolate between two colors.

        Args:
            color1: First RGB color
            color2: Second RGB color
            position: Position between colors (0.0 to 1.0)

        Returns:
            Interpolated RGB color
        """
        r = int(color1[0] + (color2[0] - color1[0]) * position)
        g = int(color1[1] + (color2[1] - color1[1]) * position)
        b = int(color1[2] + (color2[2] - color1[2]) * position)
        return (r, g, b)

    async def check_manual_override(self) -> bool:
        """Check if manual override is active.
        
        If freeze_on_manual is enabled, checks if WLED device was manually controlled.
        Note: Manual override detection is not yet fully implemented.

        Returns:
            Always returns False for now
        """
        if not self.freeze_on_manual:
            return False

        # Manual override detection requires tracking device state changes
        # and comparing with commanded state - to be implemented
        _LOGGER.debug("Manual override detection not yet implemented")
        return False

    def on_trigger(self, trigger_data: dict[str, Any]) -> None:
        """Callback for trigger events.
        
        Override this method to handle trigger events in effect implementations.

        Args:
            trigger_data: Data from triggered event
        """
        _LOGGER.debug("Trigger callback: %s", trigger_data)
        # Default implementation - subclasses can override

    @property
    def running(self) -> bool:
        """Return running state."""
        return self._running

    @property
    def last_error(self) -> str | None:
        """Return last error message."""
        return self._last_error

    @property
    def command_count(self) -> int:
        """Return total command count."""
        return self._command_count

    @property
    def success_count(self) -> int:
        """Return successful command count."""
        return self._success_count

    @property
    def failure_count(self) -> int:
        """Return failed command count."""
        return self._failure_count

    @property
    def success_rate(self) -> float:
        """Return success rate as percentage."""
        if self._command_count == 0:
            return 100.0
        return (self._success_count / self._command_count) * 100

    @property
    def running_time(self) -> float | None:
        """Return running time in seconds."""
        if self._start_time is None:
            return None
        return (datetime.now() - self._start_time).total_seconds()

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Return config schema for effect.

        Override to add effect-specific fields.

        Returns:
            JSON schema dict
        """
        return {
            "type": "object",
            "properties": {
                "effect_name": {
                    "type": "string",
                    "description": "Human-readable name for this effect",
                },
                "segment_id": {
                    "type": "integer",
                    "description": "WLED segment ID",
                    "minimum": 0,
                    "maximum": 31,
                    "default": DEFAULT_SEGMENT_ID,
                },
                "start_led": {
                    "type": "integer",
                    "description": "First LED index",
                    "minimum": 0,
                },
                "stop_led": {
                    "type": "integer",
                    "description": "Last LED index",
                    "minimum": 0,
                },
                "brightness": {
                    "type": "integer",
                    "description": "Brightness (0-255)",
                    "minimum": 0,
                    "maximum": 255,
                    "default": DEFAULT_BRIGHTNESS,
                },
                "reverse_direction": {
                    "type": "boolean",
                    "description": "Reverse LED order (flip effect)",
                    "default": DEFAULT_REVERSE_DIRECTION,
                },
                "freeze_on_manual": {
                    "type": "boolean",
                    "description": "Pause effect on manual WLED control",
                    "default": DEFAULT_FREEZE_ON_MANUAL,
                },
                "blend_mode": {
                    "type": "string",
                    "description": "How to blend multiple inputs",
                    "enum": ["average", "max", "min", "multiply", "add"],
                    "default": DEFAULT_BLEND_MODE,
                },
                "transition_mode": {
                    "type": "string",
                    "description": "Transition smoothness",
                    "enum": ["instant", "fade", "smooth"],
                    "default": DEFAULT_TRANSITION_MODE,
                },
                "zone_count": {
                    "type": "integer",
                    "description": "Number of zones to divide strip into",
                    "minimum": 1,
                    "maximum": 10,
                    "default": DEFAULT_ZONE_COUNT,
                },
                "reactive_inputs": {
                    "type": "array",
                    "description": "List of entity IDs to monitor",
                    "items": {
                        "type": "string",
                    },
                    "default": [],
                },
            },
            "required": ["effect_name"],
        }

    def get_effect_name(self) -> str:
        """Return effect name."""
        return self.__class__.__name__

    def get_effect_description(self) -> str:
        """Return effect description from docstring."""
        return self.__class__.__doc__ or "No description available"
