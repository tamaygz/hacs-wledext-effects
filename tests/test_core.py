"""Unit tests for core WLED Effects components.

These tests run without a Home Assistant instance by using the stubs injected
in conftest.py.  Only pure-logic paths are covered here — no network I/O.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Module imports — conftest.py has already injected all necessary stubs
# ---------------------------------------------------------------------------
from custom_components.wled_context_effects.data_mapper import DataMapper
from custom_components.wled_context_effects.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)
from custom_components.wled_context_effects.errors import CircuitBreakerOpenError
from custom_components.wled_context_effects.effects.base import WLEDEffectBase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bare_effect(**config_overrides: Any) -> WLEDEffectBase:
    """Return a WLEDEffectBase concrete instance with __init__ bypassed.

    We skip __init__ entirely and manually set only the attributes required by
    the methods under test, so we never need a real WLED or HA object.
    """

    class _ConcreteEffect(WLEDEffectBase):
        """Minimal concrete subclass for testing abstract base methods."""

        async def run_effect(self) -> None:  # pragma: no cover
            pass

    obj = object.__new__(_ConcreteEffect)
    # Attributes used by map_value()
    obj.value_smoother = None
    obj.input_blender = MagicMock()
    # Attributes used by check_manual_override() (not under test here but
    # avoids AttributeError if any helper touches them indirectly)
    obj.freeze_on_manual = False
    obj.json_client = None
    obj._last_commanded_on = None
    obj._last_commanded_brightness = None
    obj.__dict__.update(config_overrides)
    return obj


# ---------------------------------------------------------------------------
# DataMapper tests
# ---------------------------------------------------------------------------

class TestDataMapper:
    """Tests for DataMapper.map(), map_to_int(), and map_to_color()."""

    def test_linear_map_midpoint(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=200.0)
        assert dm.map(50.0) == pytest.approx(100.0)

    def test_linear_map_min_boundary(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=255.0)
        assert dm.map(0.0) == pytest.approx(0.0)

    def test_linear_map_max_boundary(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=255.0)
        assert dm.map(100.0) == pytest.approx(255.0)

    def test_clamp_above_max(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=255.0, clamp=True)
        assert dm.map(150.0) == pytest.approx(255.0)

    def test_clamp_below_min(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=255.0, clamp=True)
        assert dm.map(-10.0) == pytest.approx(0.0)

    def test_no_clamp_exceeds_max(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=100.0, clamp=False)
        assert dm.map(200.0) == pytest.approx(200.0)

    def test_zero_input_range_returns_midpoint_of_output(self) -> None:
        # When input_min == input_max the mapper falls back to normalized = 0.5
        dm = DataMapper(input_min=50.0, input_max=50.0, output_min=0.0, output_max=200.0)
        assert dm.map(50.0) == pytest.approx(100.0)

    def test_map_to_int_returns_integer(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=255.0)
        result = dm.map_to_int(50.0)
        assert isinstance(result, int)
        assert result == 128  # round(127.5) == 128

    def test_ease_in_curve_is_slower_at_start(self) -> None:
        linear_dm = DataMapper(
            input_min=0.0, input_max=100.0, output_min=0.0, output_max=100.0, curve="linear"
        )
        ease_in_dm = DataMapper(
            input_min=0.0, input_max=100.0, output_min=0.0, output_max=100.0, curve="ease_in"
        )
        # At 25 % of the input range, ease_in should be below linear
        assert ease_in_dm.map(25.0) < linear_dm.map(25.0)

    def test_ease_out_curve_is_faster_at_start(self) -> None:
        linear_dm = DataMapper(
            input_min=0.0, input_max=100.0, output_min=0.0, output_max=100.0, curve="linear"
        )
        ease_out_dm = DataMapper(
            input_min=0.0, input_max=100.0, output_min=0.0, output_max=100.0, curve="ease_out"
        )
        # At 25 % of the input range, ease_out should be above linear
        assert ease_out_dm.map(25.0) > linear_dm.map(25.0)

    def test_map_to_color_at_min(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=100.0)
        result = dm.map_to_color(0.0, (0, 0, 0), (255, 255, 255))
        assert result == (0, 0, 0)

    def test_map_to_color_at_max(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=100.0)
        result = dm.map_to_color(100.0, (0, 0, 0), (255, 255, 255))
        assert result == (255, 255, 255)

    def test_map_to_color_midpoint(self) -> None:
        dm = DataMapper(input_min=0.0, input_max=100.0, output_min=0.0, output_max=100.0)
        result = dm.map_to_color(50.0, (0, 0, 0), (200, 200, 200))
        assert result == (100, 100, 100)


# ---------------------------------------------------------------------------
# CircuitBreaker state-machine tests
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    """Tests for CircuitBreaker state transitions."""

    def test_initial_state_is_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, timeout=60, name="test")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed is True
        assert cb.is_open is False
        assert cb.failure_count == 0

    async def test_successful_call_passes_through(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, timeout=60, name="test")

        async def _ok() -> str:
            return "ok"

        result = await cb.call(_ok)
        assert result == "ok"
        assert cb.success_count == 1

    async def test_opens_after_failure_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, timeout=60, name="test")

        async def _fail() -> None:
            raise OSError("boom")

        for _ in range(3):
            with pytest.raises(OSError):
                await cb.call(_fail)

        assert cb.state == CircuitState.OPEN
        assert cb.is_open is True

    async def test_raises_circuit_breaker_open_error_when_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, timeout=60, name="test")

        async def _fail() -> None:
            raise OSError("boom")

        for _ in range(2):
            with pytest.raises(OSError):
                await cb.call(_fail)

        # Now the breaker is OPEN — next call must raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(_fail)

    async def test_transitions_to_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, timeout=0.05, name="test")

        async def _fail() -> None:
            raise OSError("boom")

        for _ in range(2):
            with pytest.raises(OSError):
                await cb.call(_fail)

        assert cb.is_open

        # Wait for timeout to elapse
        await asyncio.sleep(0.1)

        # Next call should be allowed through (HALF_OPEN) and succeed
        async def _ok() -> str:
            return "recovered"

        result = await cb.call(_ok)
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED

    async def test_returns_to_open_on_half_open_failure(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, timeout=0.05, name="test")

        async def _fail() -> None:
            raise OSError("boom")

        for _ in range(2):
            with pytest.raises(OSError):
                await cb.call(_fail)

        await asyncio.sleep(0.1)

        with pytest.raises(OSError):
            await cb.call(_fail)

        assert cb.state == CircuitState.OPEN

    async def test_manual_reset_restores_closed_state(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, timeout=60, name="test")

        async def _fail() -> None:
            raise OSError("boom")

        for _ in range(2):
            with pytest.raises(OSError):
                await cb.call(_fail)

        await cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


# ---------------------------------------------------------------------------
# WLEDEffectBase method tests
# ---------------------------------------------------------------------------

class TestWLEDEffectBaseParseColor:
    """Tests for WLEDEffectBase._parse_color()."""

    def test_valid_rgb_string(self) -> None:
        effect = _bare_effect()
        assert effect._parse_color("255,0,128") == (255, 0, 128)

    def test_all_zeros(self) -> None:
        effect = _bare_effect()
        assert effect._parse_color("0,0,0") == (0, 0, 0)

    def test_all_max(self) -> None:
        effect = _bare_effect()
        assert effect._parse_color("255,255,255") == (255, 255, 255)

    def test_invalid_string_returns_white(self) -> None:
        effect = _bare_effect()
        assert effect._parse_color("not_a_color") == (255, 255, 255)

    def test_too_few_parts_returns_white(self) -> None:
        effect = _bare_effect()
        assert effect._parse_color("128,64") == (255, 255, 255)

    def test_empty_string_returns_white(self) -> None:
        effect = _bare_effect()
        assert effect._parse_color("") == (255, 255, 255)

    def test_float_values_truncated(self) -> None:
        # int("1.5") raises ValueError → fallback to white
        effect = _bare_effect()
        assert effect._parse_color("1.5,2.5,3.5") == (255, 255, 255)


class TestWLEDEffectBaseInterpolateColor:
    """Tests for WLEDEffectBase.interpolate_color()."""

    def test_at_position_zero_returns_color1(self) -> None:
        effect = _bare_effect()
        result = effect.interpolate_color((0, 0, 0), (255, 255, 255), 0.0)
        assert result == (0, 0, 0)

    def test_at_position_one_returns_color2(self) -> None:
        effect = _bare_effect()
        result = effect.interpolate_color((0, 0, 0), (255, 255, 255), 1.0)
        assert result == (255, 255, 255)

    def test_midpoint_interpolation(self) -> None:
        effect = _bare_effect()
        result = effect.interpolate_color((0, 0, 0), (200, 100, 50), 0.5)
        assert result == (100, 50, 25)

    def test_result_is_rgb_tuple(self) -> None:
        effect = _bare_effect()
        result = effect.interpolate_color((10, 20, 30), (110, 120, 130), 0.5)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(c, int) for c in result)


class TestWLEDEffectBaseMapValue:
    """Tests for WLEDEffectBase.map_value(), which delegates to DataMapper."""

    def test_linear_midpoint(self) -> None:
        effect = _bare_effect()
        result = effect.map_value(50.0, 0.0, 100.0, 0.0, 200.0)
        assert result == pytest.approx(100.0)

    def test_clamped_above_max(self) -> None:
        effect = _bare_effect()
        result = effect.map_value(200.0, 0.0, 100.0, 0.0, 255.0)
        assert result == pytest.approx(255.0)

    def test_clamped_below_min(self) -> None:
        effect = _bare_effect()
        result = effect.map_value(-50.0, 0.0, 100.0, 0.0, 255.0)
        assert result == pytest.approx(0.0)

    def test_smooth_false_bypasses_smoother(self) -> None:
        """When smooth=False, value_smoother is never called."""
        effect = _bare_effect()
        smoother = MagicMock()
        effect.value_smoother = smoother
        effect.map_value(50.0, 0.0, 100.0, 0.0, 100.0, smooth=False)
        smoother.smooth.assert_not_called()

    def test_smooth_true_applies_smoother(self) -> None:
        effect = _bare_effect()
        smoother = MagicMock()
        smoother.smooth.return_value = 42.0
        effect.value_smoother = smoother
        result = effect.map_value(50.0, 0.0, 100.0, 0.0, 100.0, smooth=True)
        smoother.smooth.assert_called_once()
        assert result == 42.0
