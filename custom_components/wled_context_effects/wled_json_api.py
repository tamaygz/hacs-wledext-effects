"""WLED JSON API client for comprehensive control including per-LED operations."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .errors import ConnectionError as WLEDConnectionError, RateLimitError

_LOGGER = logging.getLogger(__name__)

# API endpoints
ENDPOINT_STATE = "/json/state"
ENDPOINT_INFO = "/json/info"
ENDPOINT_EFFECTS = "/json/eff"
ENDPOINT_PALETTES = "/json/pal"
ENDPOINT_JSON = "/json"

# Buffer size limits for per-LED control
MAX_BUFFER_ESP8266 = 10000
MAX_BUFFER_ESP32 = 24000


class WLEDJsonApiClient:
    """Client for WLED JSON API with comprehensive control including per-LED operations.
    
    This client provides full access to the WLED JSON API, enabling:
    - Per-LED color control
    - Segment management
    - Effect control
    - State queries and updates
    - Brightness and power control
    
    Properly handles buffer size limits and batching for large LED arrays.
    """

    def __init__(
        self,
        host: str,
        port: int = 80,
        session: aiohttp.ClientSession | None = None,
        timeout: int = 10,
    ) -> None:
        """Initialize WLED JSON API client.

        Args:
            host: WLED device hostname or IP address
            port: HTTP port (default 80)
            session: Optional aiohttp session to reuse
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._session = session
        self._owned_session = session is None
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._device_info: dict[str, Any] | None = None
        
        _LOGGER.debug("WLED JSON API client initialized for %s:%d", host, port)

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure aiohttp session exists."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
            self._owned_session = True
        return self._session

    async def close(self) -> None:
        """Close the client session."""
        if self._owned_session and self._session and not self._session.closed:
            try:
                await self._session.close()
            except Exception as err:
                _LOGGER.warning("Error closing session for %s: %s", self.host, err)
            finally:
                self._session = None
                _LOGGER.debug("WLED JSON API client session closed for %s", self.host)

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make HTTP request to WLED device with retry logic.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            json_data: Optional JSON payload
            max_retries: Maximum number of retry attempts for transient failures
            **kwargs: Additional aiohttp request parameters

        Returns:
            JSON response as dict

        Raises:
            WLEDConnectionError: If request fails after all retries
        """
        session = await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        last_error = None

        for attempt in range(max_retries):
            try:
                async with session.request(
                    method,
                    url,
                    json=json_data,
                    **kwargs,
                ) as response:
                    # Retry on 5xx server errors
                    if response.status >= 500 and attempt < max_retries - 1:
                        _LOGGER.warning(
                            "Server error %d from %s, retrying (attempt %d/%d)",
                            response.status, endpoint, attempt + 1, max_retries
                        )
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    
                    response.raise_for_status()
                    
                    if response.content_type == "application/json":
                        data = await response.json()
                        _LOGGER.debug("WLED API response from %s: %s", endpoint, data)
                        return data
                    else:
                        # Some endpoints may return empty response
                        _LOGGER.debug("WLED API non-JSON response from %s", endpoint)
                        return {}

            except asyncio.TimeoutError as err:
                last_error = err
                if attempt < max_retries - 1:
                    _LOGGER.warning(
                        "Timeout for %s%s, retrying (attempt %d/%d)",
                        self.base_url, endpoint, attempt + 1, max_retries
                    )
                    await asyncio.sleep(2 ** attempt)
                    continue
                _LOGGER.error("WLED API request timeout for %s%s after %d attempts", self.base_url, endpoint, max_retries)
                raise WLEDConnectionError(
                    f"WLED API request timeout after {max_retries} attempts: {self.base_url}{endpoint}"
                ) from err
            
            except aiohttp.ClientError as err:
                last_error = err
                # Retry on connection errors but not on client errors (4xx)
                if isinstance(err, (aiohttp.ClientConnectionError, aiohttp.ServerTimeoutError)) and attempt < max_retries - 1:
                    _LOGGER.warning(
                        "Connection error for %s%s: %s, retrying (attempt %d/%d)",
                        self.base_url, endpoint, err, attempt + 1, max_retries
                    )
                    await asyncio.sleep(2 ** attempt)
                    continue
                _LOGGER.error("WLED API request failed for %s%s: %s", self.base_url, endpoint, err)
                raise WLEDConnectionError(
                    f"WLED API request failed: {err}"
                ) from err
        
        # Should not reach here, but just in case
        raise WLEDConnectionError(
            f"WLED API request failed after {max_retries} attempts"
        ) from last_error

    # ========== State Management ==========

    async def get_state(self) -> dict[str, Any]:
        """Get current device state.

        Returns:
            State object with all current values
        """
        return await self._request("GET", ENDPOINT_STATE)

    async def get_info(self) -> dict[str, Any]:
        """Get device information.

        Returns:
            Info object with device details
        """
        if self._device_info is None:
            self._device_info = await self._request("GET", ENDPOINT_INFO)
        return self._device_info

    async def get_effects(self) -> list[str]:
        """Get list of available effects.

        Returns:
            List of effect names
        """
        data = await self._request("GET", ENDPOINT_EFFECTS)
        return data if isinstance(data, list) else []

    async def get_palettes(self) -> list[str]:
        """Get list of available palettes.

        Returns:
            List of palette names
        """
        data = await self._request("GET", ENDPOINT_PALETTES)
        return data if isinstance(data, list) else []

    async def set_state(self, state: dict[str, Any], return_state: bool = False) -> dict[str, Any] | None:
        """Update device state.

        Args:
            state: State object with values to update
            return_state: If True, returns full state after update

        Returns:
            Full state object if return_state=True, else None
            
        Raises:
            ValueError: If state structure is invalid
        """
        # Validate state structure
        if "bri" in state and not isinstance(state["bri"], int):
            raise ValueError(f"Invalid brightness value: {state['bri']} (must be int)")
        if "bri" in state and not 0 <= state["bri"] <= 255:
            raise ValueError(f"Brightness out of range: {state['bri']} (must be 0-255)")
        
        if "seg" in state:
            if not isinstance(state["seg"], list):
                raise ValueError("Segment data must be a list")
            for seg in state["seg"]:
                if not isinstance(seg, dict):
                    raise ValueError("Each segment must be a dict")
                if "id" in seg and not isinstance(seg["id"], int):
                    raise ValueError(f"Segment id must be int, got {type(seg['id'])}")
        
        if return_state:
            state["v"] = True
        
        return await self._request("POST", ENDPOINT_STATE, json_data=state)

    # ========== Power & Brightness ==========

    async def turn_on(self, brightness: int | None = None) -> None:
        """Turn on the light.

        Args:
            brightness: Optional brightness to set (0-255)
        """
        state: dict[str, Any] = {"on": True}
        if brightness is not None:
            state["bri"] = max(0, min(255, brightness))
        
        await self.set_state(state)
        _LOGGER.debug("Turned on WLED at %s", self.host)

    async def turn_off(self) -> None:
        """Turn off the light."""
        await self.set_state({"on": False})
        _LOGGER.debug("Turned off WLED at %s", self.host)

    async def set_brightness(self, brightness: int) -> None:
        """Set brightness.

        Args:
            brightness: Brightness level (0-255)
        """
        brightness = max(0, min(255, brightness))
        await self.set_state({"bri": brightness})
        _LOGGER.debug("Set brightness to %d at %s", brightness, self.host)

    async def toggle(self) -> bool:
        """Toggle on/off state.

        Returns:
            New state (True = on, False = off)
        """
        result = await self.set_state({"on": "t", "v": True})
        return result.get("on", False) if result else False

    # ========== Segment Control ==========

    async def update_segment(
        self,
        segment_id: int,
        **kwargs: Any,
    ) -> None:
        """Update segment properties.

        Args:
            segment_id: Segment ID (0-based)
            **kwargs: Segment properties to update (col, fx, sx, ix, pal, etc.)
        """
        segment_data = {"id": segment_id, **kwargs}
        await self.set_state({"seg": [segment_data]})
        _LOGGER.debug("Updated segment %d at %s: %s", segment_id, self.host, kwargs)

    async def set_segment_color(
        self,
        segment_id: int,
        primary: tuple[int, int, int] | None = None,
        secondary: tuple[int, int, int] | None = None,
        tertiary: tuple[int, int, int] | None = None,
    ) -> None:
        """Set segment colors.

        Args:
            segment_id: Segment ID
            primary: Primary RGB color
            secondary: Secondary RGB color
            tertiary: Tertiary RGB color
        """
        colors: list[list[int]] = []
        
        if primary is not None:
            colors.append(list(primary))
        if secondary is not None:
            colors.append(list(secondary))
        if tertiary is not None:
            colors.append(list(tertiary))
        
        if colors:
            await self.update_segment(segment_id, col=colors)

    async def set_segment_effect(
        self,
        segment_id: int,
        effect_id: int,
        speed: int | None = None,
        intensity: int | None = None,
        palette_id: int | None = None,
    ) -> None:
        """Set segment effect and parameters.

        Args:
            segment_id: Segment ID
            effect_id: Effect ID
            speed: Effect speed (0-255)
            intensity: Effect intensity (0-255)
            palette_id: Palette ID
        """
        params: dict[str, Any] = {"fx": effect_id}
        
        if speed is not None:
            params["sx"] = max(0, min(255, speed))
        if intensity is not None:
            params["ix"] = max(0, min(255, intensity))
        if palette_id is not None:
            params["pal"] = palette_id
        
        await self.update_segment(segment_id, **params)

    # ========== Per-LED Control ==========

    def _color_to_hex(self, color: tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex string.

        Args:
            color: RGB tuple (0-255 each)

        Returns:
            Hex string like "FF00AA"
        """
        return f"{color[0]:02X}{color[1]:02X}{color[2]:02X}"

    def _estimate_buffer_size(self, led_data: list[Any]) -> int:
        """Estimate JSON buffer size for LED data.

        Args:
            led_data: LED data array

        Returns:
            Estimated buffer size in bytes
        """
        # Simple estimation without JSON serialization (faster, no event loop blocking)
        # Base JSON structure: {"seg":{"i":[...]}}
        base_overhead = 20  # bytes for JSON structure
        
        # Each hex color string: "FF00AA" (6 chars) + quotes + comma = ~10 bytes
        # Each index: 1-4 digits + comma = ~5 bytes average
        bytes_per_element = 10
        
        estimated = base_overhead + (len(led_data) * bytes_per_element)
        # Add 20% safety margin
        return int(estimated * 1.2)

    async def set_individual_leds(
        self,
        segment_id: int,
        colors: list[tuple[int, int, int]],
        start_index: int = 0,
    ) -> None:
        """Set individual LED colors in a segment.

        This method handles batching automatically if the payload is too large.
        LEDs are set starting from start_index in the segment.

        Args:
            segment_id: Segment ID
            colors: List of RGB tuples
            start_index: Starting LED index in segment (default 0)
        """
        if not colors:
            return

        # Convert colors to hex strings (more efficient than RGB arrays)
        hex_colors = [self._color_to_hex(c) for c in colors]
        
        # Build LED data array with start index
        led_data: list[str | int] = []
        if start_index > 0:
            led_data.extend([start_index])
        led_data.extend(hex_colors)
        
        # Check buffer size and batch if necessary
        estimated_size = self._estimate_buffer_size(led_data)
        # Get device-specific buffer size
        max_buffer = await self.get_max_buffer_size()
        
        if estimated_size > max_buffer:
            # Need to batch
            _LOGGER.debug(
                "Batching LED data: estimated %d bytes > %d limit",
                estimated_size,
                max_buffer,
            )
            await self._set_leds_batched(segment_id, hex_colors, start_index, max_buffer)
        else:
            # Single call
            await self.update_segment(segment_id, i=led_data)
            _LOGGER.debug(
                "Set %d LEDs on segment %d at %s (single call)",
                len(colors),
                segment_id,
                self.host,
            )

    async def _set_leds_batched(
        self,
        segment_id: int,
        hex_colors: list[str],
        start_index: int = 0,
        max_buffer: int = MAX_BUFFER_ESP32,
    ) -> None:
        """Set LEDs in batches to respect buffer limits.

        Args:
            segment_id: Segment ID
            hex_colors: List of hex color strings
            start_index: Starting LED index
            max_buffer: Maximum buffer size for device
        """
        # Calculate optimal batch size based on buffer (10 bytes per LED + 20 byte overhead)
        bytes_per_led = 10
        batch_size = max(1, int((max_buffer * 0.8 - 20) / bytes_per_led))  # 80% of buffer for safety
        
        total_leds = len(hex_colors)
        total_batches = (total_leds + batch_size - 1) // batch_size
        
        _LOGGER.debug(
            "Batching %d LEDs into %d batches of ~%d LEDs (max_buffer=%d)",
            total_leds, total_batches, batch_size, max_buffer
        )
        
        for i in range(0, total_leds, batch_size):
            batch = hex_colors[i:i + batch_size]
            batch_start = start_index + i
            
            # Build LED data for this batch
            led_data: list[str | int] = [batch_start]
            led_data.extend(batch)
            
            await self.update_segment(segment_id, i=led_data)
            _LOGGER.debug(
                "Set LEDs %d-%d on segment %d (batch %d/%d)",
                batch_start,
                batch_start + len(batch) - 1,
                segment_id,
                i // batch_size + 1,
                total_batches,
            )
            
            # Small delay between batches to avoid overwhelming device (50ms)
            if i + batch_size < total_leds:
                await asyncio.sleep(0.05)

    async def set_led(
        self,
        segment_id: int,
        led_index: int,
        color: tuple[int, int, int],
    ) -> None:
        """Set a single LED color.

        Args:
            segment_id: Segment ID
            led_index: LED index within segment (0-based)
            color: RGB color tuple
        """
        hex_color = self._color_to_hex(color)
        led_data = [led_index, hex_color]
        
        await self.update_segment(segment_id, i=led_data)
        _LOGGER.debug(
            "Set LED %d to %s on segment %d at %s",
            led_index,
            hex_color,
            segment_id,
            self.host,
        )

    async def set_led_range(
        self,
        segment_id: int,
        start: int,
        stop: int,
        color: tuple[int, int, int],
    ) -> None:
        """Set a range of LEDs to the same color.

        Args:
            segment_id: Segment ID
            start: Start LED index (inclusive)
            stop: Stop LED index (inclusive)
            color: RGB color tuple
        """
        hex_color = self._color_to_hex(color)
        led_data = [start, stop, hex_color]
        
        await self.update_segment(segment_id, i=led_data)
        _LOGGER.debug(
            "Set LED range %d-%d to %s on segment %d at %s",
            start,
            stop,
            hex_color,
            segment_id,
            self.host,
        )

    async def clear_individual_leds(self, segment_id: int) -> None:
        """Clear individual LED control and unfreeze segment.

        This allows the segment to return to effect mode.

        Args:
            segment_id: Segment ID
        """
        await self.update_segment(segment_id, frz=False)
        _LOGGER.debug("Cleared individual LED control on segment %d at %s", segment_id, self.host)

    async def freeze_segment(self, segment_id: int, freeze: bool = True) -> None:
        """Freeze or unfreeze a segment.

        Args:
            segment_id: Segment ID
            freeze: True to freeze, False to unfreeze
        """
        await self.update_segment(segment_id, frz=freeze)
        _LOGGER.debug(
            "%s segment %d at %s",
            "Froze" if freeze else "Unfroze",
            segment_id,
            self.host,
        )

    # ========== Utility Methods ==========

    async def get_max_buffer_size(self) -> int:
        """Get maximum buffer size based on device architecture.

        Returns:
            Maximum buffer size in bytes
        """
        try:
            info = await self.get_info()
            arch = info.get("arch", "").lower()
            
            if "esp32" in arch:
                return MAX_BUFFER_ESP32
            else:
                return MAX_BUFFER_ESP8266
        except (WLEDConnectionError, KeyError, AttributeError) as err:
            _LOGGER.warning("Could not determine device architecture: %s, using conservative default", err)
            return MAX_BUFFER_ESP8266  # Conservative default

    async def __aenter__(self) -> WLEDJsonApiClient:
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
