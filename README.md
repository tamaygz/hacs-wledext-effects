# WLED Effects - Advanced Effects for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/tamaygz/hacs-wledext-effects.svg)](https://github.com/tamaygz/hacs-wledext-effects/releases)
[![License](https://img.shields.io/github/license/tamaygz/hacs-wledext-effects.svg)](LICENSE)

Transform your WLED LED strips into smart, context-aware displays that react to your Home Assistant state! Create stunning visualizations, notifications, and ambient lighting with 9 powerful effects and advanced programmability.

## ✨ Key Features

- **🎨 9 Built-in Effects**: From ambient rainbows to attention-grabbing alerts
- **🔄 Context-Aware**: React to sensors, states, and events in real-time
- **🎯 Multi-Zone Control**: Divide strips into independent zones
- **⚡ Trigger System**: Event-based effect modulation
- **📊 Data Visualization**: Transform sensor data into LED patterns
- **🎚️ Full Control**: Complete entity support (Switch, Number, Select, Sensor, Button)
- **⚡ High Performance**: Async architecture, rate limiting, circuit breaker
- **📱 HACS Ready**: One-click installation

## 📋 Requirements

- **Home Assistant** 2024.1.0 or newer
- **WLED Integration** (installed first)
- **WLED Device** with firmware 0.14.0+

## 🚀 Installation

### Via HACS (Recommended)

1. **Open HACS** in Home Assistant
2. Click **⋮** (three dots) → **Custom repositories**
3. Add repository URL:
   ```
   https://github.com/tamaygz/hacs-wledext-effects
   ```
4. Select category: **Integration**
5. Click **Add**
6. Search for **"WLED Effects"** in HACS
7. Click **Download**
8. **Restart Home Assistant**
9. Go to **Settings** → **Devices & Services** → **Add Integration**
10. Search for **"WLED Effects"**

📖 **[Complete Installation Guide](docs/INSTALLATION.md)**

## ⚡ Quick Start

```yaml
# 1. Add the integration (via UI)
# 2. Select your WLED device
# 3. Choose an effect (try Rainbow Wave!)
# 4. Turn it on!

service: switch.turn_on
target:
  entity_id: switch.wled_context_effects_rainbow_wave
```

📖 **[5-Minute Quick Start Guide](docs/QUICK_START.md)**

## 🎨 Effects

| Effect | Purpose | Best For |
|--------|---------|----------|
| **Rainbow Wave** | Flowing rainbow animation | Decoration, ambient lighting |
| **Segment Fade** | Color transitions | Mood lighting |
| **Loading** | Moving progress bar | Progress indicators |
| **State Sync** | Data visualization | Sensor monitoring |
| **Breathe** | Gentle pulsing | Notifications, alerts |
| **Meter** | Gauge/bar chart | CPU, battery, temperature |
| **Sparkle** | Twinkling effect | Activity indicators |
| **Chase** | Scanner animation | Processing, retro effects |
| **Alert** | Multi-severity alerts | Security, warnings |

📖 **[Complete Effects Reference](docs/EFFECTS_REFERENCE.md)**

## 💡 Example Use Cases

### Temperature Visualization

```yaml
effect_type: state_sync
config:
  state_entity: sensor.living_room_temperature
  min_value: 15
  max_value: 30
  color_low: "0,0,255"    # Blue (cold)
  color_high: "255,0,0"   # Red (hot)
  animation_mode: fill
```

### CPU Usage Monitor

```yaml
effect_type: meter
config:
  state_entity: sensor.processor_use
  threshold_medium: 60
  threshold_high: 85
  show_peak: true
  # Green <60%, yellow 60-85%, red >85%
```

### Security Alert

```yaml
effect_type: alert
config:
  severity: critical
  pattern: strobe
  acknowledge_entity: input_boolean.security_ack
  max_duration: 300
```

### Motion-Activated Rainbow

```yaml
automation:
  - alias: "Motion Rainbow"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion
        to: 'on'
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.wled_context_effects_rainbow_wave
```

## 🎯 Advanced Features

### Context-Aware

Effects react to your smart home in real-time:

- **Multi-Input Blending**: Combine multiple sensors
- **Trigger System**: Respond to events, thresholds, time
- **Data Mapping**: Transform values with interpolation curves
- **Smooth Transitions**: Eliminate jittery sensor readings
- **Manual Override**: Pause automation on manual control

### Multi-Zone Control

Divide your LED strip into independent zones:

```yaml
effect_type: state_sync
config:
  zone_count: 3
  # Zone 0: CPU
  # Zone 1: Memory
  # Zone 2: Disk
```

### State-Driven Effects

Every effect can optionally react to Home Assistant states:

```yaml
effect_type: breathe
config:
  pulse_rate: 1.0
  state_entity: sensor.notification_priority
  state_controls: rate
  # Higher priority = faster pulse
```

📖 **[Context-Aware Features Guide](docs/CONTEXT_AWARE_FEATURES.md)**  
📖 **[Advanced Guide](docs/ADVANCED_GUIDE.md)**

## 📚 Documentation

### Getting Started
- **[Installation Guide](docs/INSTALLATION.md)** - Detailed installation instructions
- **[Quick Start Guide](docs/QUICK_START.md)** - Your first effect in 5 minutes
- **[Effects Reference](docs/EFFECTS_REFERENCE.md)** - All 9 effects documented

### Advanced
- **[Context-Aware Features](docs/CONTEXT_AWARE_FEATURES.md)** - Smart home integration
- **[Advanced Guide](docs/ADVANCED_GUIDE.md)** - Triggers, automation, optimization
- **[Services API](docs/SERVICES_API.md)** - Service reference
- **[Effect Development](docs/EFFECT_DEVELOPMENT.md)** - Create custom effects

### Support
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[GitHub Issues](https://github.com/tamaygz/hacs-wledext-effects/issues)** - Report bugs
- **[GitHub Discussions](https://github.com/tamaygz/hacs-wledext-effects/discussions)** - Ask questions

## 🛠️ Entities Created

Each effect creates these entities:

| Entity | Purpose | Example |
|--------|---------|---------|
| **Switch** | Turn effect on/off | `switch.wled_context_effects_rainbow_wave` |
| **Number** | Brightness, speed | `number.wled_context_effects_rainbow_wave_brightness` |
| **Select** | Effect modes | `select.wled_context_effects_state_sync_animation_mode` |
| **Sensor** | Status, stats | `sensor.wled_context_effects_rainbow_wave_frame_rate` |
| **Button** | Restart effect | `button.wled_context_effects_rainbow_wave_restart` |

## 🔧 Custom Effects

Create your own effects - they're auto-discovered!

```python
from .base import WLEDEffectBase
from .registry import register_effect

@register_effect
class MyEffect(WLEDEffectBase):
    """My custom effect."""
    
    async def run_effect(self) -> None:
        """Effect logic here."""
        # Your code...
```

Place in `custom_components/wled_context_effects/effects/` and restart!

📖 **[Effect Development Guide](docs/EFFECT_DEVELOPMENT.md)**

## 🤝 Contributing

Contributions welcome! 

- **Effects**: Create and share new effects
- **Documentation**: Improve guides and examples
- **Bug Reports**: Help us improve quality
- **Feature Requests**: Suggest new capabilities

## 🙏 Acknowledgments

- **Home Assistant Core Team**
- **WLED Project**
- **HACS Team**
- Inspired by: LedFx, Adaptive Lighting, Sound Reactive WLED

---

## 🆕 Version History

- **v1.0.0** - Initial release with 9 effects, context-aware features, full documentation
- Core effects: Rainbow Wave, Segment Fade, Loading, State Sync
- Advanced effects: Breathe, Meter, Sparkle, Chase, Alert
- Context-aware system with triggers, multi-input, data mapping
- Complete entity support and automation integration

---

**Made with ❤️ for the Home Assistant community**

**Repository**: [hacs-wledext-effects](https://github.com/tamaygz/hacs-wledext-effects)  
**Version**: 1.0.0

