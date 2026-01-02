# Effects Quick Reference

## All Available Effects (9 Total)

### Classic Effects (v1.0)

| Effect | Purpose | Key Features | Use Cases |
|--------|---------|--------------|-----------|
| **Rainbow Wave** | Animated rainbow | Flowing colors, adjustable speed/length | Decoration, ambient lighting |
| **Segment Fade** | Color transitions | Smooth fades between colors | Mood lighting, transitions |
| **Loading** | Progress bar | Moving bar with trail | Progress indicators, animations |
| **State Sync** | Data visualization | Multi-mode state display | CPU/battery/temp monitoring |

### Context-Aware Effects (v2.1)

| Effect | Purpose | Key Features | Use Cases |
|--------|---------|--------------|-----------|
| **Breathe/Pulse** | Notifications | Smooth pulsing, rate control | Alerts, notifications, meditation |
| **Meter/Gauge** | Metrics display | Fill bar, threshold colors | CPU, battery, temperature gauges |
| **Sparkle/Twinkle** | Activity indicator | Random twinkles, density control | Network activity, message counters |
| **Chase/Scanner** | Directional animation | Moving pattern, KITT mode | Processing, data flow, classic look |
| **Alert/Notification** | Attention-grabbing alerts | Multi-severity, 8 patterns, acknowledgment | Security alerts, warnings, critical notifications |

---

## State-Reactive Capability Matrix

All effects support optional state input with different control modes:

| Effect | State Controls | Options |
|--------|----------------|---------|
| **Rainbow Wave** | `speed`, `wavelength`, `both` | Speed: 1-100, Wavelength: 10-200 LEDs |
| **Segment Fade** | `speed`, `position` | Speed: 0.1x-10x, Position: 0-100% |
| **Loading** | `speed`, `position`, `bar_size` | Speed: 0.01-1.0s, Position: 0-100%, Size: 1-50 LEDs |
| **State Sync** | Advanced multi-input | See CONTEXT_AWARE_FEATURES.md |
| **Breathe** | `rate`, `intensity`, `both` | Rate: 0.1-10 Hz, Intensity: 50-255 |
| **Meter** | Direct fill level | Fill: 0-100%, threshold colors |
| **Sparkle** | `density`, `speed`, `both` | Density: 0.01-1.0, Fade rate: 0.5-0.95 |
| **Chase** | `speed`, `direction`, `length`, `both` | Speed: 0.001-0.5s, Length: 1-20 LEDs |
| **Alert** | Auto-severity from state | Threshold-based severity mapping, acknowledgment |

---

## Feature Support

All effects support the complete feature set:

| Feature | Support | Notes |
|---------|---------|-------|
| **Reverse Direction** | ✅ All | Flip LED order |
| **Multi-Zone** | ✅ All | Independent zones |
| **State Input** | ✅ All | Optional StateSourceCoordinator |
| **Data Mapping** | ✅ All | Smooth value transitions |
| **Trigger System** | ✅ All | Event-based modulation |
| **Blend Modes** | ✅ All | Multi-input blending |
| **Manual Override** | ✅ All | Freeze on manual control |
| **Smoothing** | ✅ All | Exponential smoothing |

---

## Selection Guide

### Choose by Purpose:

**Decoration / Ambient:**
- Rainbow Wave (flowing colors)
- Sparkle (starfield)
- Segment Fade (color transitions)

**Data Visualization:**
- Meter (gauges, progress)
- State Sync (multi-mode display)
- Loading (progress bars)

**Notifications / Alerts:**
- Alert (multi-severity, most configurable)
- Breathe (calming/gentle alerts)
- Sparkle (activity burst)
- Chase (directional indicator)

**Status Indicators:**
- Meter (levels, percentages)
- Breathe (intensity levels)
- Chase (processing state)

**Activity / Processing:**
- Sparkle (random activity)
- Chase (directional flow)
- Loading (movement)

---

## Configuration Patterns

### Standalone (No State)
```yaml
effect_name: breathe
config:
  color: "0,100,255"
  pulse_rate: 1.0
  # Works independently
```

### State-Driven
```yaml
effect_name: meter
config:
  state_entity: sensor.cpu_usage
  # Directly visualizes state
```

### Multi-Input with Blending
```yaml
effect_name: sparkle
config:
  state_entity: sensor.network_activity
  reactive_inputs:
    - sensor.cpu_usage
    - sensor.disk_io
  blend_mode: average
  # Combines multiple inputs
```

### Triggered
```yaml
effect_name: breathe
config:
  pulse_rate: 1.0
  triggers:
    - trigger_type: state_change
      entity_id: binary_sensor.motion
      # Pulse on motion
```

---

## Performance

| Effect | CPU Load | Memory | Update Rate |
|--------|----------|--------|-------------|
| Rainbow Wave | Low | Minimal | 20 FPS |
| Segment Fade | Low | Minimal | 20 FPS |
| Loading | Low | Minimal | 20 FPS |
| State Sync | Low-Med | Low | 20 FPS |
| Breathe | Low | Minimal | 20 FPS |
| Meter | Low | Minimal | 20 FPS |
| Sparkle | Med | Low | 20 FPS |
| Chase | Low | Minimal | Variable |
| Alert | Low-Med | Low | 20 FPS |

All effects:
- Non-blocking async
- Efficient LED updates
- Minimal state tracking
- Graceful degradation

---

## Documentation Links

- **[README.md](README.md)** - Main integration documentation
- **[CONTEXT_AWARE_FEATURES.md](CONTEXT_AWARE_FEATURES.md)** - Advanced features guide
- **[STATE_REACTIVE_EFFECTS.md](STATE_REACTIVE_EFFECTS.md)** - Classic effects with state
- **[NEW_EFFECTS_GUIDE.md](NEW_EFFECTS_GUIDE.md)** - v2.1 effects detailed guide

---

## Version History

- **v1.0**: Rainbow Wave, Segment Fade, Loading, State Sync
- **v2.0**: Context-aware features (zones, triggers, data mapping)
- **v2.1**: New effects (Breathe, Meter, Sparkle, Chase) with full feature integration
- **v2.2**: Alert effect - Multi-severity notification system with 8 patterns, acknowledgment, and auto-escalation
