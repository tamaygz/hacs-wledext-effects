# Per-LED Control Quick Reference

## 🚀 Quick Start

```python
# In your effect class
async def run_effect(self) -> None:
    # Generate colors
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    
    # Set LEDs
    if self.json_client:
        await self.set_individual_leds(colors)
    else:
        await self.send_wled_command(color_primary=colors[0])
```

## 📋 Methods Available

### Set Multiple LEDs
```python
await self.set_individual_leds(
    colors=[(255, 0, 0), (0, 255, 0), (0, 0, 255)],
    start_index=0  # Optional
)
```
- **Auto-batches** if array is large
- **Respects** buffer limits
- **Handles errors** automatically

### Set Single LED
```python
await self.set_led(
    led_index=10,
    color=(255, 0, 0)
)
```

### Set LED Range
```python
await self.set_led_range(
    start=0,
    stop=19,
    color=(255, 0, 0)
)
```
- All LEDs 0-19 set to same color
- More efficient than individual

### Clear Per-LED Control
```python
await self.clear_individual_leds()
```
- Unfreezes segment
- Returns to effect mode

## 🎨 Color Format

**Input**: RGB tuples
```python
(255, 0, 0)     # Red
(0, 255, 0)     # Green
(0, 0, 255)     # Blue
(255, 255, 255) # White
```

**Internal**: Hex strings (automatic)
```python
"FF0000"  # Red
"00FF00"  # Green
"0000FF"  # Blue
"FFFFFF"  # White
```

## 📊 Batching

### Automatic
- Arrays > 256 LEDs automatically batched
- 50ms delay between batches
- No manual intervention needed

### Manual Control
```python
# Client handles automatically
await self.set_individual_leds(colors_for_500_leds)
# Internally splits into:
#   Batch 1: LEDs 0-255
#   Batch 2: LEDs 256-499
```

## 🔧 Effect Template

```python
from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

@register_effect
class MyEffect(WLEDEffectBase):
    """My custom effect with per-LED control."""
    
    def __init__(
        self,
        hass,
        wled_client,
        config,
        json_client=None,  # Add this parameter
    ):
        super().__init__(hass, wled_client, config, json_client)
        # Your init code
    
    async def run_effect(self):
        # Generate colors
        led_count = (self.stop_led - self.start_led) + 1
        colors = [self.generate_color(i) for i in range(led_count)]
        
        # Apply reverse if configured
        colors = self.apply_reverse(colors)
        
        # Use per-LED control with fallback
        if self.json_client:
            try:
                await self.set_individual_leds(colors)
            except Exception as err:
                _LOGGER.warning("Per-LED failed: %s", err)
                await self.send_wled_command(
                    on=True,
                    brightness=self.brightness,
                    color_primary=colors[0],
                )
        else:
            await self.send_wled_command(
                on=True,
                brightness=self.brightness,
                color_primary=colors[0],
            )
        
        # Control update rate
        await asyncio.sleep(0.05)  # 20 Hz
```

## ⚡ Performance Tips

### Update Rates
```python
# Fast (20 Hz)
await asyncio.sleep(0.05)   # Good for small arrays

# Medium (10 Hz)
await asyncio.sleep(0.10)   # Good for medium arrays

# Slow (5 Hz)
await asyncio.sleep(0.20)   # Good for large arrays
```

### Buffer Limits
- **ESP8266**: ~150-200 LEDs per request
- **ESP32**: ~350-400 LEDs per request
- Client auto-detects and batches

### Optimization
```python
# Good: Generate exact colors needed
colors = [self.calc_color(i) for i in range(led_count)]

# Bad: Generate unnecessary colors
colors = [self.calc_color(i) for i in range(1000)][:led_count]
```

## 🛡️ Error Handling

### Basic
```python
if self.json_client:
    await self.set_individual_leds(colors)
else:
    await self.send_wled_command(color_primary=colors[0])
```

### Advanced
```python
if self.json_client:
    try:
        await self.set_individual_leds(colors)
    except WLEDConnectionError as err:
        _LOGGER.error("Connection error: %s", err)
        # Fallback or retry
    except Exception as err:
        _LOGGER.warning("Per-LED failed: %s", err)
        # Fallback
else:
    # No JSON client - use basic command
    await self.send_wled_command(color_primary=colors[0])
```

## 📏 Common Patterns

### Gradient Effect
```python
async def run_effect(self):
    led_count = (self.stop_led - self.start_led) + 1
    colors = []
    
    for i in range(led_count):
        # Calculate position (0.0 to 1.0)
        pos = i / led_count
        
        # Interpolate between two colors
        color = self.interpolate_color(
            self.color_start,
            self.color_end,
            pos
        )
        colors.append(color)
    
    if self.json_client:
        await self.set_individual_leds(colors)
```

### Fill Effect
```python
async def run_effect(self):
    led_count = (self.stop_led - self.start_led) + 1
    fill_count = int(self.level * led_count)
    
    colors = []
    for i in range(led_count):
        if i < fill_count:
            colors.append(self.fill_color)
        else:
            colors.append(self.background_color)
    
    if self.json_client:
        await self.set_individual_leds(colors)
```

### Zone Effect
```python
async def run_effect(self):
    colors = []
    
    for zone_idx in range(self.zone_count):
        zone_start, zone_stop = self.map_to_zone(zone_idx)
        zone_color = self.get_zone_color(zone_idx)
        
        zone_leds = (zone_stop - zone_start) + 1
        colors.extend([zone_color] * zone_leds)
    
    if self.json_client:
        await self.set_individual_leds(colors)
```

## 🎯 Best Practices

1. **Always check `json_client`** before using per-LED
2. **Provide fallback** to basic command
3. **Handle errors** gracefully
4. **Use appropriate update rates** for LED count
5. **Generate exact colors needed** (no waste)
6. **Log performance issues** (> 100ms updates)
7. **Test with various LED counts** (small, medium, large)
8. **Consider network latency** in your timings

## 🔍 Debugging

### Check If Per-LED Active
```python
if self.json_client:
    _LOGGER.info("Per-LED control available")
else:
    _LOGGER.warning("Per-LED control not available, using fallback")
```

### Monitor Performance
```python
import time

start = time.time()
await self.set_individual_leds(colors)
duration = time.time() - start

if duration > 0.1:
    _LOGGER.warning(
        "Slow update: %.2fs for %d LEDs",
        duration,
        len(colors)
    )
```

### Check Success Rate
```python
_LOGGER.info(
    "Command stats: %d total, %d success, %.1f%% rate",
    self.command_count,
    self.success_count,
    self.success_rate
)
```

## 📖 More Info

- **Full Docs**: `docs/README_PER_LED_CONTROL.md`
- **Examples**: `effects/meter.py`, `effects/rainbow_wave.py`
- **API Reference**: `wled_json_api.py`
- **Architecture**: `ARCHITECTURE_DIAGRAM.md`

## 🆘 Common Issues

### "JSON client not available"
**Problem**: Trying to use per-LED without client  
**Solution**: Check `if self.json_client` before calling methods

### "Buffer overflow"
**Problem**: Payload too large for device  
**Solution**: Automatic batching handles this

### "Slow updates"
**Problem**: Update rate too high for LED count  
**Solution**: Increase sleep time in `run_effect()`

### "Connection timeout"
**Problem**: Network latency or device offline  
**Solution**: Already handled, check logs for issues

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/tamaygz/hacs-wledext-effects/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tamaygz/hacs-wledext-effects/discussions)
- **Docs**: [Documentation](docs/)
