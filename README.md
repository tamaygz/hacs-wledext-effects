# WLED Effects Integration for Home Assistant

**Version 2.0 - Context-Aware Architecture**

A modern, modular Home Assistant integration for managing advanced WLED effects with real-time synchronization, state monitoring, programmable triggers, and comprehensive entity controls.

> **🆕 Version 2.0 Features**: Context-aware effects with flip/reverse, multi-zone control, reactive inputs, advanced data mapping, trigger system, blend modes, and smooth transitions! See [CONTEXT_AWARE_FEATURES.md](CONTEXT_AWARE_FEATURES.md) for full details.

## ✨ Features

### Core Features
- **🎨 Advanced Effects**: 4 pre-built effects (Rainbow Wave, Segment Fade, Loading, State Sync) with extensible framework
- **🔄 Real-time State Sync**: Monitor Home Assistant entities and visualize their states on LEDs
- **📊 Live Monitoring**: Real-time stats tracking (frame rate, latency, error rate)
- **🛠️ Full Entity Controls**: Switch, Number, Select, Sensor, and Button entities for complete effect management
- **⚡ High Performance**: Async architecture with rate limiting and circuit breaker
- **🧩 Modular Design**: Extensible effect system with auto-discovery
- **🏠 Native HA Integration**: Built with modern HA patterns (DataUpdateCoordinator, CoordinatorEntity)
- **📱 HACS Ready**: Fully compliant with HACS requirements

### 🆕 Context-Aware Features (v2.0)
- **🔄 Flip/Reverse Direction**: Invert LED order for any effect (e.g., loading bar goes right-to-left)
- **🎯 Multi-Zone Control**: Divide strips into up to 10 independent zones
- **📡 Reactive Inputs**: Monitor multiple HA entities simultaneously
- **📈 Advanced Data Mapping**: Value mapping with interpolation curves (linear, ease-in, ease-out, ease-in-out)
- **⚡ Trigger System**: Event-based effect modulation (state change, threshold, time, custom events)
- **🎨 Blend Modes**: Combine multiple inputs (average, max, min, multiply, add)
- **🔀 Smooth Transitions**: Exponential smoothing eliminates jittery sensor effects
- **✋ Manual Override Detection**: Automatically pause automation on manual WLED control (like Adaptive Lighting)

**[📖 See Full Context-Aware Documentation](CONTEXT_AWARE_FEATURES.md)**

## 📋 Requirements

- Home Assistant 2024.1.0 or newer
- WLED device with firmware 0.14.0 or newer
- Python 3.11 or newer

## 🚀 Quick Start

### Installation via HACS

1. Add this repository to HACS as a custom repository
2. Install "WLED Effects"
3. Restart Home Assistant
4. Go to Settings → Devices & Services → Add Integration → "WLED Effects"

### Basic Usage

```yaml
# Start a temperature-reactive effect
service: wled_effects.start_effect
data:
  device_id: my_wled
  effect_name: state_sync
  config:
    state_entity: sensor.living_room_temperature
    min_value: 15
    max_value: 30
    color_low: "0,0,255"    # Blue for cold
    color_high: "255,0,0"   # Red for hot
    animation_mode: fill
    transition_mode: smooth
```

## 🎨 Built-in Effects

### 1. Rainbow Wave
Animated rainbow that flows across the LED strip with configurable speed and wavelength.

```yaml
service: wled_effects.start_effect
data:
  effect_name: rainbow_wave
  config:
    wave_speed: 10.0
    wave_length: 60
    reverse_direction: false  # Set true to reverse
```

### 2. Segment Fade
Smooth color transitions between multiple colors.

```yaml
service: wled_effects.start_effect
data:
  effect_name: segment_fade
  config:
    color1: "255,0,0"
    color2: "0,0,255"
    transition_speed: 2.0
```

### 3. Loading
Loading bar animation with trail effects.

```yaml
service: wled_effects.start_effect
data:
  effect_name: loading
  config:
    color: "0,255,0"
    bar_size: 10
    speed: 0.05
    reverse_direction: true  # Bar moves right-to-left
    trail_fade: true
```

### 4. State Sync (Context-Aware)
Visualize Home Assistant entity states with multiple animation modes.

```yaml
service: wled_effects.start_effect
data:
  effect_name: state_sync
  config:
    state_entity: sensor.cpu_usage
    min_value: 0
    max_value: 100
    animation_mode: fill      # fill, center, dual, solid
    color_low: "0,255,0"      # Green for low
    color_high: "255,0,0"     # Red for high
    transition_mode: smooth   # Smooth sensor readings
    reverse_direction: false
```

## 🎯 Advanced Use Cases

### Multi-Sensor Ambient Lighting
```yaml
service: wled_effects.start_effect
data:
  effect_name: state_sync
  config:
    state_entity: sensor.ambient_light
    reactive_inputs:
      - sensor.ambient_light
      - sensor.motion_activity
      - sensor.circadian_brightness
    blend_mode: max
    freeze_on_manual: true  # Pause if manually adjusted
    transition_mode: smooth
```

### Threshold-Triggered Effects
```yaml
# Effect configuration with trigger
config:
  state_entity: sensor.server_temperature
  trigger_config:
    trigger_type: threshold
    entity_id: sensor.server_temperature
    threshold: 70
    comparison: ">"
    # Fires callback when temp > 70°C
```

## 🛠️ Services

### `wled_effects.start_effect`
Start an effect with configuration.

### `wled_effects.stop_effect`
Stop the currently running effect.

### `wled_effects.update_effect_config`
Update effect configuration without restarting.

### `wled_effects.get_effect_stats`
Get performance metrics for running effect.

## 📊 Entities

Each integration creates:
- **Switch**: Effect on/off, auto-restart
- **Number**: Brightness, speed, LED range
- **Select**: Effect selection, animation modes
- **Sensor**: Status, frame rate, latency, error rate, uptime
- **Button**: Restart effect, clear stats

## 🧩 Creating Custom Effects

```python
from ..effects.base import WLEDEffectBase
from ..effects.registry import register_effect

@register_effect
class MyEffect(WLEDEffectBase):
    """My custom effect."""
    
    async def run_effect(self) -> None:
        """Effect logic."""
        # Check manual override
        if await self.check_manual_override():
            return
        
        # Generate colors
        colors = self._generate_colors()
        
        # Apply reverse if configured
        colors = self.apply_reverse(colors)
        
        # Send to WLED
        await self.send_wled_command(
            on=True,
            brightness=self.brightness,
            color_primary=colors[0],
        )
```

Place in `custom_components/wled_effects/effects/` and it will be auto-discovered!

## 📚 Documentation

- **[Context-Aware Features Guide](CONTEXT_AWARE_FEATURES.md)** - Complete guide to v2.0 features
- **[Implementation Status](IMPLEMENTATION_COMPLETE.md)** - Development completion summary
- **[Verification Checklist](VERIFICATION_CHECKLIST.md)** - Quality assurance checks

## 🤝 Contributing

Contributions welcome! See our documentation for:
- Effect development guide
- Architecture overview
- Testing procedures

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Home Assistant Core Team
- WLED Project
- HACS Team
- Inspired by: LedFx, Adaptive Lighting, Sound Reactive WLED

---

**Made with ❤️ for the Home Assistant community**

**Repository**: [hacs-wledext-effects](https://github.com/tamaygz/hacs-wledext-effects)  
**Version**: 2.0 - Context-Aware Architecture  
**Status**: ✅ Core Complete - Context-Aware Features Implemented

