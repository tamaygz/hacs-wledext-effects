"""TextEffect and StateTextEffect – scrolling text on a WLED 2D LED matrix."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..errors import EffectExecutionError
from .base import WLEDEffectBase
from .registry import register_effect

_LOGGER = logging.getLogger(__name__)

# WLED names tried in order when resolving the Scrolling Text effect ID.
_SCROLLING_TEXT_NAMES = (
    "Scrolling Text",
    "2D Scrolling Text",
    "Scroll Text",
)
# Common fallback FX ID for WLED 0.14+ firmware.
_SCROLLING_TEXT_FALLBACK_FX_ID = 122


def _parse_rgb(value: Any, default: list[int]) -> list[int]:
    """Parse an RGB value from 'R,G,B' string, list/tuple, or return default."""
    if value is None:
        return list(default)
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return [max(0, min(255, int(v))) for v in value[:3]]
    if isinstance(value, str):
        try:
            parts = [max(0, min(255, int(x.strip()))) for x in value.split(",")]
            if len(parts) == 3:
                return parts
        except (ValueError, AttributeError):
            pass
    return list(default)


@register_effect
class TextEffect(WLEDEffectBase):
    """Display scrolling text on a WLED 2D LED matrix.

    Uses WLED's built-in Scrolling Text effect.  Matrix dimensions and the
    2D segment configuration are auto-detected from the device at setup time;
    manual overrides are available via ``matrix_width`` / ``matrix_height``
    config keys.

    Config keys
    -----------
    text            : str   – Text to scroll (default "WLED")
    scroll_speed    : int   – Marquee speed 0-255 (default 128)
    font_size       : int   – 1-4 (default 1 = smallest)
    direction       : str   – "left" | "right" (default "left")
    text_color      : str   – Foreground "R,G,B" (default "255,255,255")
    bg_color        : str   – Background "R,G,B" (default "0,0,0")
    update_interval : float – Seconds between re-sends (default 1.0)
    matrix_width    : int   – Override auto-detected columns
    matrix_height   : int   – Override auto-detected rows
    fx_id           : int   – Override auto-resolved effect ID
    """

    def __init__(
        self,
        hass: Any,
        wled_client: Any,
        config: dict[str, Any],
        json_client: Any = None,
    ) -> None:
        super().__init__(hass, wled_client, config, json_client)
        self._load_text_config()

        # Populated at setup() – not from config
        self._scrolling_text_fx_id: int | None = None
        self._is_2d: bool = False
        self._matrix_width: int | None = None
        self._matrix_height: int | None = None
        self._seg_width: int | None = None
        self._seg_height: int | None = None

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_text_config(self) -> None:
        """Read text-specific keys from self.config into instance attrs."""
        self.text: str = str(self.config.get("text", "WLED"))
        self.scroll_speed: int = max(0, min(255, int(self.config.get("scroll_speed", 128))))
        self.font_size: int = max(1, min(4, int(self.config.get("font_size", 1))))
        self.direction: str = str(self.config.get("direction", "left"))
        self.text_color: list[int] = _parse_rgb(self.config.get("text_color"), [255, 255, 255])
        self.bg_color: list[int] = _parse_rgb(self.config.get("bg_color"), [0, 0, 0])
        self.update_interval: float = max(0.1, float(self.config.get("update_interval", 1.0)))

    def reload_config(self) -> None:
        super().reload_config()
        self._load_text_config()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    async def setup(self) -> bool:
        if not await super().setup():
            return False
        if self.json_client is None:
            _LOGGER.error("TextEffect requires a JSON API client")
            return False
        await asyncio.gather(
            self._detect_matrix_settings(),
            self._resolve_fx_id(),
        )
        return True

    async def run_once(self) -> None:
        """Run effect once, lazily resolving fx_id if setup() was not called."""
        if self._scrolling_text_fx_id is None:
            if self.json_client is None:
                from ..errors import EffectExecutionError
                raise EffectExecutionError("TextEffect requires a JSON API client")
            await asyncio.gather(
                self._detect_matrix_settings(),
                self._resolve_fx_id(),
            )
        await super().run_once()

    async def _detect_matrix_settings(self) -> None:
        """Auto-detect 2D matrix dimensions and segment info from WLED device."""
        try:
            info, state = await asyncio.gather(
                self.json_client.get_info(),
                self.json_client.get_state(),
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Could not auto-detect matrix settings: %s", err)
            return

        # ── Global 2D matrix from /json/info ──────────────────────────
        leds_info = info.get("leds", {}) if isinstance(info, dict) else {}
        matrix_info = leds_info.get("matrix")  # only present when 2D is enabled in WLED
        if isinstance(matrix_info, dict):
            self._is_2d = True
            self._matrix_width = matrix_info.get("w")
            self._matrix_height = matrix_info.get("h")
            _LOGGER.info(
                "WLED 2D matrix detected: %s×%s (%s total LEDs)",
                self._matrix_width,
                self._matrix_height,
                leds_info.get("count", "?"),
            )
        else:
            _LOGGER.info(
                "WLED info.leds.matrix absent — device may not be configured as 2D."
            )

        # Apply manual config overrides
        if self.config.get("matrix_width") is not None:
            self._matrix_width = int(self.config["matrix_width"])
        if self.config.get("matrix_height") is not None:
            self._matrix_height = int(self.config["matrix_height"])

        # ── Per-segment dimensions from /json/state ────────────────────
        segments = state.get("seg", []) if isinstance(state, dict) else []
        for seg in segments:
            if not isinstance(seg, dict) or seg.get("id") != self.segment_id:
                continue
            w = seg.get("w")
            h = seg.get("h")
            if w and h and int(w) > 1:
                self._seg_width = int(w)
                self._seg_height = int(h)
                self._is_2d = True
                _LOGGER.debug(
                    "Segment %d is 2D: %d×%d",
                    self.segment_id,
                    self._seg_width,
                    self._seg_height,
                )
            _LOGGER.debug(
                "Segment %d range: start=%s stop=%s",
                self.segment_id,
                seg.get("start"),
                seg.get("stop"),
            )
            break

        if not self._is_2d:
            _LOGGER.warning(
                "TextEffect: no 2D segment detected on segment %d. "
                "Configure 2D in WLED Settings > LED Preferences for best results.",
                self.segment_id,
            )

    async def _resolve_fx_id(self) -> None:
        """Resolve WLED Scrolling Text effect ID from device effect list."""
        # Allow hard-coded override from config
        if self.config.get("fx_id") is not None:
            self._scrolling_text_fx_id = int(self.config["fx_id"])
            _LOGGER.debug("Using configured fx_id=%d", self._scrolling_text_fx_id)
            return

        try:
            effects: list[str] = await self.json_client.get_effects()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Could not fetch effects list: %s — using fallback fx=%d",
                err,
                _SCROLLING_TEXT_FALLBACK_FX_ID,
            )
            self._scrolling_text_fx_id = _SCROLLING_TEXT_FALLBACK_FX_ID
            return

        # Exact match first
        for name in _SCROLLING_TEXT_NAMES:
            if name in effects:
                self._scrolling_text_fx_id = effects.index(name)
                _LOGGER.debug(
                    "Resolved '%s' → fx=%d", name, self._scrolling_text_fx_id
                )
                return

        # Case-insensitive fallback
        lower_effects = [e.lower() for e in effects]
        for name in _SCROLLING_TEXT_NAMES:
            try:
                idx = lower_effects.index(name.lower())
                self._scrolling_text_fx_id = idx
                _LOGGER.debug(
                    "Resolved '%s' → fx=%d (case-insensitive)", effects[idx], idx
                )
                return
            except ValueError:
                continue

        _LOGGER.warning(
            "Scrolling Text effect not found in WLED effects list (%d effects). "
            "Using fallback fx=%d. Add fx_id to config to override. Searched: %s",
            len(effects),
            _SCROLLING_TEXT_FALLBACK_FX_ID,
            _SCROLLING_TEXT_NAMES,
        )
        self._scrolling_text_fx_id = _SCROLLING_TEXT_FALLBACK_FX_ID

    # ------------------------------------------------------------------
    # Effect execution
    # ------------------------------------------------------------------

    async def _send_text(self, text: str) -> None:
        """Push text and display parameters to WLED via JSON API."""
        if self.json_client is None:
            raise EffectExecutionError("TextEffect requires a JSON API client")

        fx_id = (
            self._scrolling_text_fx_id
            if self._scrolling_text_fx_id is not None
            else _SCROLLING_TEXT_FALLBACK_FX_ID
        )

        # font_size 1-4  →  c1 0/64/128/192
        # WLED maps SEGMENT.custom1 >> 6 to select from 4 built-in font sizes.
        c1_value = (self.font_size - 1) * 64

        await self.json_client.update_segment(
            self.segment_id,
            fx=int(fx_id),
            sx=self.scroll_speed,
            ix=128,          # intensity — not visually significant for Scrolling Text
            c1=c1_value,
            col=[self.text_color, self.bg_color, [0, 0, 0]],
            rev=(self.direction == "right"),
            n=text[:255],    # WLED segment `n` field = text for Scrolling Text effect
        )
        _LOGGER.debug(
            "Sent text=%r fx=%d speed=%d dir=%s font=%d seg=%d",
            text,
            fx_id,
            self.scroll_speed,
            self.direction,
            self.font_size,
            self.segment_id,
        )

    async def run_effect(self) -> None:
        await self._send_text(self.text)
        await asyncio.sleep(self.update_interval)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_effect_name(self) -> str:
        return "TextEffect"

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        schema = super().config_schema()
        schema.setdefault("properties", {}).update(
            {
                "text": {
                    "type": "string",
                    "default": "WLED",
                    "description": "Text to display",
                },
                "scroll_speed": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "default": 128,
                    "description": "Marquee speed (0=slow, 255=fast)",
                },
                "font_size": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4,
                    "default": 1,
                    "description": "Font size 1–4 (small→large)",
                },
                "direction": {
                    "type": "string",
                    "enum": ["left", "right"],
                    "default": "left",
                    "description": "Scroll direction",
                },
                "text_color": {
                    "type": "string",
                    "default": "255,255,255",
                    "description": "Foreground color as R,G,B",
                },
                "bg_color": {
                    "type": "string",
                    "default": "0,0,0",
                    "description": "Background color as R,G,B",
                },
                "update_interval": {
                    "type": "number",
                    "default": 1.0,
                    "description": "Seconds between re-sends to WLED (device handles animation)",
                },
                "matrix_width": {
                    "type": "integer",
                    "description": "Override auto-detected matrix column count",
                },
                "matrix_height": {
                    "type": "integer",
                    "description": "Override auto-detected matrix row count",
                },
                "fx_id": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "description": "Override auto-resolved Scrolling Text effect ID",
                },
            }
        )
        return schema


@register_effect
class StateTextEffect(TextEffect):
    """Display a Home Assistant entity state as scrolling text on a WLED 2D matrix.

    Monitors a HA entity (and optional attribute).  When the state value changes
    the matrix text is updated on the next effect cycle.  A ``text_template``
    controls how the value is rendered, e.g. ``"Temp: {state} °C"``.

    Additional config keys (inherits all TextEffect keys)
    -------------------------------------------------------
    state_entity    : str   – HA entity ID to monitor (required)
    state_attribute : str   – Attribute to use instead of main state (optional)
    text_template   : str   – Format string; ``{state}`` is replaced with the value
    update_interval : float – Poll interval in seconds (default 5.0; state-change
                              events also trigger an immediate update)
    """

    def __init__(
        self,
        hass: Any,
        wled_client: Any,
        config: dict[str, Any],
        json_client: Any = None,
    ) -> None:
        # state_entity / state_attribute must be in config BEFORE super().__init__
        # because WLEDEffectBase.__init__ reads them from config.
        super().__init__(hass, wled_client, config, json_client)
        self._load_state_text_config()
        self._last_formatted: str | None = None

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_state_text_config(self) -> None:
        self.text_template: str = str(self.config.get("text_template", "{state}"))
        # Default update_interval is slower than TextEffect — state events drive updates
        if "update_interval" not in self.config:
            self.update_interval = 5.0

    def reload_config(self) -> None:
        super().reload_config()
        self._load_state_text_config()

    # ------------------------------------------------------------------
    # Effect execution
    # ------------------------------------------------------------------

    def _format_state(self, raw_value: Any) -> str:
        """Apply text_template to the raw state/attribute value."""
        try:
            return self.text_template.format(state=raw_value)
        except (KeyError, ValueError, IndexError, AttributeError):
            return str(raw_value)

    async def run_effect(self) -> None:
        if self.state_coordinator is None:
            # No entity configured — fall back to static text
            await self._send_text(self.text)
            await asyncio.sleep(self.update_interval)
            return

        raw_value = self.state_coordinator.data
        if raw_value is None:
            await asyncio.sleep(self.update_interval)
            return

        formatted = self._format_state(raw_value)
        if formatted != self._last_formatted:
            self._last_formatted = formatted
            await self._send_text(formatted)

        await asyncio.sleep(self.update_interval)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_effect_name(self) -> str:
        return "StateTextEffect"

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        schema = super().config_schema()
        schema.setdefault("properties", {}).update(
            {
                "state_entity": {
                    "type": "string",
                    "description": "HA entity ID whose state/attribute is displayed",
                },
                "state_attribute": {
                    "type": "string",
                    "description": "Entity attribute to display (omit for main state value)",
                },
                "text_template": {
                    "type": "string",
                    "default": "{state}",
                    "description": "Format string; {state} is replaced with the entity value",
                },
                "update_interval": {
                    "type": "number",
                    "default": 5.0,
                    "description": "Polling interval in seconds (state-change events also trigger updates)",
                },
            }
        )
        return schema
