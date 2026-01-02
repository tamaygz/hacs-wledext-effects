# Effect Development Guide

Create your own custom WLED effects for the integration.

## Overview

The WLED Effects integration uses a modular, registry-based system that automatically discovers new effects.

## Quick Start

### 1. Create Effect File

Create a new file in `custom_components/wled_context_effects/effects/`:

```python
# my_effect.py
from .base import WLEDEffectBase
from .registry import register_effect

@register_effect
class MyEffect(WLEDEffectBase):
    """My custom effect."""
    
    async def run_effect(self) -> None:
        """Main effect loop."""
        while self.running:
            # Your effect logic here
            await asyncio.sleep(0.05)  # 20 FPS
```

### 2. Implement Effect Logic

```python
async def run_effect(self) -> None:
    """Render the effect."""
    position = 0
    
    while self.running:
        # Check manual override
        if await self.check_manual_override():
            await asyncio.sleep(0.1)
            continue
        
        # Generate colors
        color = self._calculate_color(position)
        
        # Send to WLED
        await self.send_wled_command(
            on=True,
            brightness=self.brightness,
            color_primary=color,
        )
        
        # Update position
        position = (position + 1) % self.led_count
        
        await asyncio.sleep(0.05)
```

### 3. Test Your Effect

1. Restart Home Assistant
2. Add integration, select "My Effect"
3. Test!

## Base Class API

### Properties

```python
self.hass              # Home Assistant instance
self.wled_client       # WLED client for API calls
self.config            # Effect configuration dict
self.running           # Is effect running?
self.led_count         # Number of LEDs
self.brightness        # Current brightness (0-255)
self.reverse_direction # Flip LED order?
self.zone_count        # Number of zones
```

### Methods

```python
# Core
await self.setup()                    # Initialize effect
await self.start()                    # Start effect
await self.stop()                     # Stop effect
async def run_effect(self) -> None:  # Override this!

# WLED Communication
await self.send_wled_command(**kwargs)  # Send command to WLED

# Utilities
self.apply_reverse(led_array)        # Apply reverse if configured
self.map_to_zone(zone_index)         # Get LED range for zone
self.map_value(value, ...)           # Map value with smoothing
await self.check_manual_override()   # Check for manual control

# Colors
self.interpolate_color(c1, c2, pos)  # Interpolate between colors
```

## Configuration Schema

Define your effect's configuration parameters:

```python
EFFECT_SCHEMA = {
    "my_parameter": {
        "type": "number",
        "default": 10.0,
        "min": 1.0,
        "max": 100.0,
    },
    "my_color": {
        "type": "string",
        "default": "255,0,0",
    },
    "my_mode": {
        "type": "select",
        "options": ["mode1", "mode2", "mode3"],
        "default": "mode1",
    },
}
```

## State-Reactive Effects

Add state support:

```python
from ..coordinator import StateSourceCoordinator

class MyEffect(WLEDEffectBase):
    async def setup(self) -> bool:
        # Setup state coordinator
        if self.config.get("state_entity"):
            self.state_coordinator = StateSourceCoordinator(
                self.hass,
                self.config["state_entity"],
                self.config.get("state_attribute"),
            )
            await self.state_coordinator.async_setup()
        
        return await super().setup()
    
    def _get_state_value(self) -> float:
        """Get normalized state value (0.0-1.0)."""
        if not hasattr(self, 'state_coordinator'):
            return 0.5
        
        raw = self.state_coordinator.get_numeric_value(
            self.state_min, self.state_max
        )
        return (raw - self.state_min) / (self.state_max - self.state_min)
```

## Examples

### Example 1: Pulse Effect

```python
@register_effect
class PulseEffect(WLEDEffectBase):
    """Simple pulsing effect."""
    
    async def run_effect(self) -> None:
        import math
        position = 0
        
        while self.running:
            if await self.check_manual_override():
                await asyncio.sleep(0.1)
                continue
            
            # Calculate brightness (sine wave)
            brightness = int(128 + 127 * math.sin(position * 0.1))
            
            # Get color from config
            color = self.config.get("color", "255,0,0")
            
            # Send to WLED
            await self.send_wled_command(
                on=True,
                brightness=brightness,
                color_primary=color,
            )
            
            position += 1
            await asyncio.sleep(0.05)
```

### Example 2: State-Driven Bar

```python
@register_effect
class StateBarEffect(WLEDEffectBase):
    """Bar that fills based on state."""
    
    async def run_effect(self) -> None:
        while self.running:
            if await self.check_manual_override():
                await asyncio.sleep(0.1)
                continue
            
            # Get state value (0.0-1.0)
            state_value = self._get_state_value()
            
            # Calculate fill percentage
            fill_leds = int(self.led_count * state_value)
            
            # Generate LED colors
            colors = []
            for i in range(self.led_count):
                if i < fill_leds:
                    colors.append("0,255,0")  # Green (filled)
                else:
                    colors.append("50,0,0")   # Dim red (empty)
            
            # Apply reverse if configured
            colors = self.apply_reverse(colors)
            
            # Send to WLED (simplified - actual impl varies)
            await self.send_wled_command(
                on=True,
                brightness=self.brightness,
                color_primary=colors[0] if colors else "0,255,0",
            )
            
            await asyncio.sleep(0.1)
```

## Best Practices

1. **Always check `self.running`** in loops
2. **Use `await self.check_manual_override()`** to respect manual control
3. **Include `await asyncio.sleep()`** to prevent blocking
4. **Handle errors gracefully** with try/except
5. **Document your effect** with docstrings
6. **Test thoroughly** before sharing

## Testing

1. **Unit tests**: Test effect logic
2. **Integration tests**: Test with real WLED device
3. **Performance tests**: Check frame rate, latency
4. **Error handling**: Test failure modes

## Sharing Your Effect

1. Create PR on GitHub
2. Include documentation
3. Add examples
4. Test on multiple devices

---

**Last Updated**: January 2026
