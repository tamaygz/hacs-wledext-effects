# Per-LED Control

The WLED Context Effects integration provides comprehensive per-LED control capabilities through the WLED JSON API. This allows effects to set individual LED colors for precise, pixel-level control.

## Overview

Traditional WLED effects set segment-level colors (primary, secondary, tertiary) which apply to entire segments. Per-LED control allows each LED to have its own color, enabling:

- True gradients and smooth color transitions
- Meter/gauge visualizations with color zones
- Complex animated patterns
- Pixel-perfect synchronization with Home Assistant states

## Architecture

The integration uses two communication methods:

1. **python-wled library**: For basic segment control, device info, and state queries
2. **WLEDJsonApiClient**: For per-LED control via WLED JSON API

Both clients are managed by `WLEDConnectionManager` and effects can use either or both.

## JSON API Client

### Features

- **Per-LED color control**: Set individual LED colors via segment.i property
- **Automatic batching**: Handles large LED arrays by splitting into manageable chunks
- **Buffer size limits**: Respects ESP8266 (10KB) and ESP32 (24KB) buffer limits
- **Error handling**: Comprehensive error handling with retries
- **Connection pooling**: Reuses sessions for efficiency
- **Async/await**: Fully async for Home Assistant integration

### Usage in Effects

Effects receive both clients during initialization:

```python
class MyEffect(WLEDEffectBase):
    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict[str, Any],
        json_client: WLEDJsonApiClient | None = None,
    ) -> None:
        super().__init__(hass, wled_client, config, json_client)
```

### Per-LED Control Methods

The base class provides convenience methods for per-LED control:

#### Set Multiple LEDs

```python
# Generate color array for all LEDs
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # RGB tuples

# Set all LEDs at once (automatically batches if needed)
await self.set_individual_leds(colors, start_index=0)
```

#### Set Single LED

```python
# Set LED 10 to red
await self.set_led(led_index=10, color=(255, 0, 0))
```

#### Set LED Range

```python
# Set LEDs 0-19 to blue
await self.set_led_range(start=0, stop=19, color=(0, 0, 255))
```

#### Clear Per-LED Control

```python
# Return segment to effect mode (unfreeze)
await self.clear_individual_leds()
```

## Example: Meter Effect

The meter effect demonstrates per-LED control for gradient visualization:

```python
async def run_effect(self) -> None:
    # Generate color array based on level and thresholds
    colors: list[tuple[int, int, int]] = []
    
    led_count = (self.stop_led - self.start_led) + 1
    fill_leds = int((self.current_level / 100.0) * led_count)
    
    for i in range(led_count):
        if i < fill_leds:
            led_level = ((i + 1) / led_count) * 100.0
            colors.append(self._get_color_for_level(led_level))
        else:
            colors.append(self.background_color)
    
    # Apply reverse direction
    colors = self.apply_reverse(colors)
    
    # Set LEDs with automatic fallback
    if self.json_client:
        await self.set_individual_leds(colors)
    else:
        # Fallback to basic command
        await self.send_wled_command(
            on=True,
            brightness=self.brightness,
            color_primary=colors[0],
        )
```

## Example: Rainbow Wave Effect

The rainbow wave effect uses per-LED control for smooth gradients:

```python
async def run_effect(self) -> None:
    colors: list[tuple[int, int, int]] = []
    led_count = (self.stop_led - self.start_led) + 1
    
    for i in range(led_count):
        # Calculate hue for smooth rainbow
        hue = ((i / self.wave_length) + self.color_offset) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        color = (
            int(rgb[0] * 255),
            int(rgb[1] * 255),
            int(rgb[2] * 255),
        )
        colors.append(color)
    
    colors = self.apply_reverse(colors)
    
    # Use per-LED control for true rainbow
    if self.json_client:
        await self.set_individual_leds(colors)
    else:
        await self.send_wled_command(
            on=True,
            brightness=self.brightness,
            color_primary=colors[0],
        )
    
    self.color_offset = (self.color_offset + self.wave_speed / 100.0) % 1.0
```

## Performance Considerations

### Buffer Limits

WLED devices have limited JSON buffer sizes:
- **ESP8266**: ~10KB
- **ESP32**: ~24KB

The JSON API client automatically:
1. Estimates payload size
2. Batches if over limit
3. Adds delays between batches (50ms)

### Update Rate

Per-LED updates are more expensive than segment updates. Recommended rates:

- **Simple effects** (solid colors): 20+ Hz (50ms interval)
- **Animated effects** (gradients): 10-20 Hz (50-100ms interval)
- **Complex effects** (many LEDs): 5-10 Hz (100-200ms interval)

### Batching

For large LED arrays (>256 LEDs), the client automatically batches:

```python
# This call may be split into multiple API requests
await self.set_individual_leds(colors_for_500_leds)
```

Default batch size: 256 LEDs per request

### Network Latency

Consider network latency when setting update rates:
- Local network: Usually <10ms
- WiFi: Can vary 10-50ms
- Poor connection: May exceed 100ms

Add error handling and consider longer intervals if commands fail frequently.

## JSON API Details

### Endpoint

`POST /json/state`

### Per-LED Format

```json
{
  "seg": {
    "id": 0,
    "i": [
      0,           // Start index
      "FF0000",    // LED 0: Red (hex format)
      "00FF00",    // LED 1: Green
      "0000FF",    // LED 2: Blue
      19,          // Start new range at index 19
      "FFFFFF"     // LED 19: White
    ]
  }
}
```

### Hex Color Format

Colors are specified as 6-character hex strings:
- `"FF0000"` = Red (255, 0, 0)
- `"00FF00"` = Green (0, 255, 0)
- `"0000FF"` = Blue (0, 0, 255)
- `"FFFFFF"` = White (255, 255, 255)

More efficient than RGB array format.

### Range Format

Set multiple LEDs to same color:

```json
{
  "seg": {
    "i": [0, 19, "FF0000"]  // LEDs 0-19: Red
  }
}
```

### Freezing

Setting individual LEDs automatically freezes the segment (pauses built-in effects). Clear with:

```json
{
  "seg": {
    "id": 0,
    "frz": false
  }
}
```

## Error Handling

### JSON Client Not Available

Always check if JSON client is available:

```python
if self.json_client:
    await self.set_individual_leds(colors)
else:
    # Fallback to basic command
    await self.send_wled_command(color_primary=colors[0])
```

### Command Failures

The base class tracks success/failure counts:

```python
# Check success rate
success_rate = self.success_rate  # Percentage

# Check last error
if self.last_error:
    _LOGGER.warning("Last error: %s", self.last_error)
```

### Connection Errors

JSON client raises `WLEDConnectionError` for connection issues:

```python
from ..errors import WLEDConnectionError

try:
    await self.set_individual_leds(colors)
except WLEDConnectionError as err:
    _LOGGER.error("Connection failed: %s", err)
    # Fallback or retry logic
```

## Best Practices

### 1. Always Provide Fallback

```python
if self.json_client:
    try:
        await self.set_individual_leds(colors)
    except Exception as err:
        _LOGGER.warning("Per-LED failed: %s", err)
        await self.send_wled_command(color_primary=colors[0])
else:
    await self.send_wled_command(color_primary=colors[0])
```

### 2. Respect Update Rates

```python
async def run_effect(self) -> None:
    # ... generate colors ...
    await self.set_individual_leds(colors)
    
    # Wait before next update (50ms = 20 Hz)
    await asyncio.sleep(0.05)
```

### 3. Use Appropriate Color Resolution

For smooth gradients, generate enough colors:

```python
# Good: One color per LED
led_count = (self.stop_led - self.start_led) + 1
colors = [generate_color(i) for i in range(led_count)]
```

### 4. Log Performance Issues

```python
start_time = time.time()
await self.set_individual_leds(colors)
duration = time.time() - start_time

if duration > 0.1:  # 100ms threshold
    _LOGGER.warning("Slow per-LED update: %.2fs for %d LEDs", duration, len(colors))
```

### 5. Consider Segment Freezing

If you need built-in WLED effects to remain active, avoid per-LED control or explicitly unfreeze:

```python
# Your custom effect
await self.set_individual_leds(colors)

# ... later, return control to WLED ...
await self.clear_individual_leds()  # Unfreezes segment
```

## Limitations

1. **No per-LED control via python-wled**: The python-wled library doesn't support per-LED control, requiring direct JSON API usage
2. **Buffer size limits**: Large LED arrays must be batched
3. **Segment freezing**: Per-LED control freezes built-in WLED effects
4. **Network overhead**: More data = slower updates compared to segment-level commands
5. **ESP8266 memory**: Limited RAM may cause issues with very large LED arrays

## Future Enhancements

Potential improvements for future versions:

- **Compression**: Use WLED's hex color range format for repeated colors
- **Delta updates**: Only send changed LEDs (requires state tracking)
- **Hardware detection**: Automatically adjust batch size based on device architecture
- **Adaptive rates**: Adjust update rate based on network latency
- **Persistent freeze state**: Remember segment freeze state across restarts

## References

- [WLED JSON API Documentation](https://kno.wled.ge/interfaces/json-api/)
- [WLED Segment API](https://kno.wled.ge/features/segments/)
- [WLED GitHub Repository](https://github.com/Aircoookie/WLED)
