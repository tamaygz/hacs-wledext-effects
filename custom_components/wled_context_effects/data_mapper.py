"""Data mapping utilities for WLED effects."""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class DataMapper:
    """Advanced data mapping and interpolation for effect parameters.
    
    Maps input values from one range to another with various interpolation modes.
    Supports clamping, scaling, and non-linear mappings.
    """

    def __init__(
        self,
        input_min: float = 0.0,
        input_max: float = 100.0,
        output_min: float = 0.0,
        output_max: float = 255.0,
        clamp: bool = True,
        curve: str = "linear",
    ) -> None:
        """Initialize data mapper.

        Args:
            input_min: Minimum input value
            input_max: Maximum input value
            output_min: Minimum output value
            output_max: Maximum output value
            clamp: Whether to clamp output to range
            curve: Interpolation curve (linear, ease_in, ease_out, ease_in_out)
        """
        self.input_min = input_min
        self.input_max = input_max
        self.output_min = output_min
        self.output_max = output_max
        self.clamp = clamp
        self.curve = curve

    def map(self, value: float) -> float:
        """Map input value to output range.

        Args:
            value: Input value

        Returns:
            Mapped output value
        """
        # Normalize to 0-1
        input_range = self.input_max - self.input_min
        if input_range == 0:
            normalized = 0.5
        else:
            normalized = (value - self.input_min) / input_range

        # Apply curve
        if self.curve == "ease_in":
            normalized = normalized ** 2
        elif self.curve == "ease_out":
            normalized = 1 - (1 - normalized) ** 2
        elif self.curve == "ease_in_out":
            if normalized < 0.5:
                normalized = 2 * normalized ** 2
            else:
                normalized = 1 - 2 * (1 - normalized) ** 2
        # else: linear (no change)

        # Map to output range
        output_range = self.output_max - self.output_min
        output = self.output_min + (normalized * output_range)

        # Clamp if requested
        if self.clamp:
            output = max(self.output_min, min(self.output_max, output))

        return output

    def map_to_int(self, value: float) -> int:
        """Map and convert to integer.

        Args:
            value: Input value

        Returns:
            Mapped integer value
        """
        return int(round(self.map(value)))

    def map_to_color(
        self,
        value: float,
        color_low: tuple[int, int, int],
        color_high: tuple[int, int, int],
    ) -> tuple[int, int, int]:
        """Map value to color between two colors.

        Args:
            value: Input value
            color_low: RGB color for minimum value
            color_high: RGB color for maximum value

        Returns:
            Interpolated RGB color
        """
        # Normalize value
        input_range = self.input_max - self.input_min
        if input_range == 0:
            position = 0.5
        else:
            position = (value - self.input_min) / input_range

        if self.clamp:
            position = max(0.0, min(1.0, position))

        # Interpolate each color channel
        r = int(color_low[0] + (color_high[0] - color_low[0]) * position)
        g = int(color_low[1] + (color_high[1] - color_low[1]) * position)
        b = int(color_low[2] + (color_high[2] - color_low[2]) * position)

        return (r, g, b)


class MultiInputBlender:
    """Blend multiple input values using various blend modes.
    
    Combines data from multiple sources into a single value for effect rendering.
    """

    @staticmethod
    def blend(values: list[float], mode: str = "average") -> float:
        """Blend multiple values using specified mode.

        Args:
            values: List of input values
            mode: Blend mode (average, max, min, multiply, add)

        Returns:
            Blended value
        """
        if not values:
            return 0.0

        if mode == "average":
            return sum(values) / len(values)
        elif mode == "max":
            return max(values)
        elif mode == "min":
            return min(values)
        elif mode == "multiply":
            result = 1.0
            for v in values:
                result *= v
            return result
        elif mode == "add":
            return sum(values)
        else:
            _LOGGER.warning("Unknown blend mode %s, using average", mode)
            return sum(values) / len(values)

    @staticmethod
    def blend_colors(
        colors: list[tuple[int, int, int]],
        mode: str = "average",
    ) -> tuple[int, int, int]:
        """Blend multiple RGB colors.

        Args:
            colors: List of RGB tuples
            mode: Blend mode

        Returns:
            Blended RGB color
        """
        if not colors:
            return (0, 0, 0)

        if len(colors) == 1:
            return colors[0]

        # Blend each channel separately
        r_values = [c[0] for c in colors]
        g_values = [c[1] for c in colors]
        b_values = [c[2] for c in colors]

        return (
            int(MultiInputBlender.blend(r_values, mode)),
            int(MultiInputBlender.blend(g_values, mode)),
            int(MultiInputBlender.blend(b_values, mode)),
        )


class ValueSmoother:
    """Smooth value changes over time to prevent jittery effects.
    
    Uses exponential moving average for smoothing.
    """

    def __init__(self, alpha: float = 0.3) -> None:
        """Initialize smoother.

        Args:
            alpha: Smoothing factor (0-1, lower = smoother)
        """
        self.alpha = alpha
        self.current_value: float | None = None

    def smooth(self, new_value: float) -> float:
        """Apply smoothing to new value.

        Args:
            new_value: New input value

        Returns:
            Smoothed value
        """
        if self.current_value is None:
            self.current_value = new_value
            return new_value

        # Exponential moving average
        self.current_value = (
            self.alpha * new_value + (1 - self.alpha) * self.current_value
        )
        return self.current_value

    def reset(self) -> None:
        """Reset smoother state."""
        self.current_value = None
