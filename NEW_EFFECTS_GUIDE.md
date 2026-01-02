# Context-Aware Effects Guide

## New Effects (v2.1)

This guide documents the 4 new context-aware effects designed specifically for data visualization, notifications, and ambient intelligence.

---

## 1. Breathe/Pulse Effect

**File:** `breathe.py`

### Overview
Creates a smooth, calming breathing or pulsing pattern using sine wave brightness modulation. Perfect for notifications, alerts, status indicators, and ambient lighting.

### Context-Aware Capabilities
- **Pulse rate** controlled by state (slow/calming → fast/urgent)
- **Intensity** controlled by state (subtle → bright)
- **Color** can represent notification type or status
- **Trigger-based** pulsing (pulse N times on events via trigger system)
- **Multi-zone** support for independent breathing zones

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `color` | string | "0,100,255" | LED color (R,G,B format) |
| `pulse_rate` | number | 1.0 | Breathing rate in cycles/second (0.1-10.0) |
| `min_brightness` | integer | 10 | Minimum brightness (0-255) |
| `max_brightness` | integer | 255 | Maximum brightness (0-255) |
| `easing` | string | "sine" | Easing function: sine, linear, ease_in_out |
| `state_entity` | string | - | Optional: Entity to control parameters |
| `state_attribute` | string | - | Optional: Attribute to monitor |
| `state_controls` | string | "rate" | What state controls: rate, intensity, both |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

### Use Cases

#### 1. Notification Urgency Indicator
```yaml
- name: "Notification Pulse"
  effect_type: "breathe"
  color: "255,100,0"  # Orange
  state_entity: "sensor.notification_priority"
  state_controls: "rate"
  state_min: 0
  state_max: 10
  # Low priority = slow pulse, high priority = fast pulse
```

#### 2. Sleep/Meditation Timer
```yaml
- name: "Calming Breathe"
  effect_type: "breathe"
  color: "0,50,150"  # Dim blue
  pulse_rate: 0.2  # 12 breaths/minute
  easing: "sine"
  min_brightness: 5
  max_brightness: 50
```

#### 3. System Status with Intensity
```yaml
- name: "System Load Pulse"
  effect_type: "breathe"
  color: "100,200,255"
  state_entity: "sensor.cpu_usage"
  state_controls: "intensity"
  state_min: 0
  state_max: 100
  # Higher CPU = brighter pulse
```

---

## 2. Meter/Gauge Effect

**File:** `meter.py`

### Overview
Visualizes numeric values as a filling bar with threshold-based colors. Perfect for CPU, battery, temperature, progress tracking, and any metric visualization.

### Context-Aware Capabilities
- **Fill level** directly from state value
- **Color gradients** based on threshold ranges (green/yellow/red)
- **Multiple fill modes** (bottom-up, center-out, bidirectional)
- **Peak indicators** (optional white marker at maximum)
- **Smooth transitions** with data mapping
- **Multi-zone** support for multiple metrics simultaneously

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fill_mode` | string | "bottom_up" | How meter fills: bottom_up, center_out, bidirectional |
| `default_level` | number | 50.0 | Default level when no state (0-100) |
| `color_low` | string | "0,255,0" | Color for low values (green) |
| `color_medium` | string | "255,255,0" | Color for medium values (yellow) |
| `color_high` | string | "255,0,0" | Color for high values (red) |
| `threshold_medium` | number | 50.0 | Threshold for medium color (0-100) |
| `threshold_high` | number | 80.0 | Threshold for high color (0-100) |
| `show_peak` | boolean | false | Show peak level indicator |
| `background_color` | string | "10,10,10" | Background for unfilled area |
| `state_entity` | string | - | Entity to visualize |
| `state_attribute` | string | - | Optional: Attribute to monitor |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

### Use Cases

#### 1. CPU Usage Monitor
```yaml
- name: "CPU Meter"
  effect_type: "meter"
  fill_mode: "bottom_up"
  state_entity: "sensor.processor_use"
  state_min: 0
  state_max: 100
  threshold_medium: 60
  threshold_high: 85
  show_peak: true
  # Green <60%, yellow 60-85%, red >85%
```

#### 2. Battery Level Display
```yaml
- name: "Battery Gauge"
  effect_type: "meter"
  fill_mode: "bottom_up"
  state_entity: "sensor.phone_battery"
  color_low: "255,0,0"    # Red for low battery
  color_medium: "255,165,0"  # Orange for medium
  color_high: "0,255,0"   # Green for high
  threshold_medium: 30
  threshold_high: 70
```

#### 3. Temperature Visualization
```yaml
- name: "Temperature Meter"
  effect_type: "meter"
  fill_mode: "center_out"  # Emanate from center
  state_entity: "sensor.living_room_temperature"
  state_min: 15
  state_max: 30
  color_low: "0,0,255"    # Cold = blue
  color_medium: "0,255,0" # Comfortable = green
  color_high: "255,0,0"   # Hot = red
  threshold_medium: 20
  threshold_high: 26
```

#### 4. Multi-Zone System Monitor
```yaml
- name: "System Stats"
  effect_type: "meter"
  fill_mode: "bottom_up"
  zone_count: 3
  # Zone 1: CPU, Zone 2: Memory, Zone 3: Disk
  # Configure zones separately
```

---

## 3. Sparkle/Twinkle Effect

**File:** `sparkle.py`

### Overview
Creates a twinkling starfield effect where random pixels light up and fade out. Density and speed can represent activity levels, notification counts, or ambient conditions.

### Context-Aware Capabilities
- **Sparkle density** controlled by state (sparse → dense)
- **Fade speed** controlled by state (slow twinkle → fast)
- **Activity visualization** (more activity = more sparkles)
- **Color variation** (optional random hue shifts)
- **Trigger bursts** (sparkle burst on events)
- **Multi-zone** independent twinkling

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sparkle_color` | string | "255,255,255" | Sparkle color (R,G,B format) |
| `background_color` | string | "0,0,20" | Background color |
| `density` | number | 0.1 | Sparkle density (0.0-1.0) |
| `fade_rate` | number | 0.8 | How fast sparkles fade (0.0-1.0) |
| `color_variation` | boolean | false | Enable random hue variation |
| `state_entity` | string | - | Optional: Entity to control parameters |
| `state_attribute` | string | - | Optional: Attribute to monitor |
| `state_controls` | string | "density" | What state controls: density, speed, both |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

### Use Cases

#### 1. Network Activity Indicator
```yaml
- name: "Network Sparkles"
  effect_type: "sparkle"
  sparkle_color: "0,255,255"  # Cyan
  background_color: "0,0,10"
  state_entity: "sensor.network_throughput_mb"
  state_controls: "density"
  state_min: 0
  state_max: 100
  # More network traffic = more sparkles
```

#### 2. Notification Counter
```yaml
- name: "Unread Messages"
  effect_type: "sparkle"
  sparkle_color: "255,100,200"  # Pink
  state_entity: "sensor.unread_message_count"
  state_controls: "both"  # Density and speed
  state_min: 0
  state_max: 50
  color_variation: true
```

#### 3. Ambient Starfield
```yaml
- name: "Starfield"
  effect_type: "sparkle"
  sparkle_color: "200,200,255"
  background_color: "0,0,30"
  density: 0.05  # Sparse
  fade_rate: 0.95  # Slow fade
  color_variation: true
```

#### 4. Smart Home Activity
```yaml
- name: "Home Activity"
  effect_type: "sparkle"
  state_entity: "sensor.active_devices_count"
  state_controls: "density"
  state_min: 0
  state_max: 20
  # More active devices = busier sparkles
```

---

## 4. Chase/Scanner Effect

**File:** `chase.py`

### Overview
Creates a Knight Rider / Cylon style scanning effect or chase pattern where a group of LEDs moves along the strip. Direction and speed represent data flow, activity, or processing.

### Context-Aware Capabilities
- **Chase speed** controlled by state (slow → fast)
- **Direction** controllable or triggered
- **Length** adjustable dynamically
- **Scanner mode** (Cylon/KITT style fade from center)
- **Chase mode** (moving block with tail)
- **Bounce or wrap** at boundaries
- **Multi-zone** independent chases

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chase_color` | string | "255,100,0" | Chase color (R,G,B format) |
| `background_color` | string | "0,0,0" | Background color |
| `chase_length` | integer | 5 | Length of chase in LEDs (1-50) |
| `speed` | number | 0.05 | Movement speed (delay between steps) |
| `fade_tail` | boolean | true | Fade the tail of the chase |
| `bounce` | boolean | true | Bounce at ends (vs wrap around) |
| `scan_mode` | boolean | false | Scanner mode (Cylon/KITT style) |
| `state_entity` | string | - | Optional: Entity to control parameters |
| `state_attribute` | string | - | Optional: Attribute to monitor |
| `state_controls` | string | "speed" | What state controls: speed, direction, length, both |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

### Use Cases

#### 1. Data Processing Indicator
```yaml
- name: "Processing Chase"
  effect_type: "chase"
  chase_color: "0,255,100"
  chase_length: 8
  fade_tail: true
  state_entity: "sensor.processing_queue_length"
  state_controls: "speed"
  state_min: 0
  state_max: 100
  # More items in queue = faster chase
```

#### 2. Classic KITT Scanner
```yaml
- name: "KITT Scanner"
  effect_type: "chase"
  chase_color: "255,0,0"
  scan_mode: true
  chase_length: 10
  bounce: true
  speed: 0.03
  fade_tail: true
```

#### 3. Directional Data Flow
```yaml
- name: "Data Flow"
  effect_type: "chase"
  chase_color: "100,200,255"
  state_entity: "sensor.network_direction"  # -1 to 1
  state_controls: "direction"
  state_min: -1
  state_max: 1
  # Negative = left, positive = right
```

#### 4. Download Progress
```yaml
- name: "Download Progress"
  effect_type: "chase"
  chase_color: "0,255,0"
  state_entity: "sensor.download_percentage"
  state_controls: "length"
  state_min: 0
  state_max: 100
  bounce: false  # Wrap around
  # Chase length grows with progress
```

---

## Advanced Integration Examples

### 1. Multi-Effect Notification System
```yaml
automation:
  - alias: "Priority Notification"
    trigger:
      - platform: state
        entity_id: sensor.notification_priority
    action:
      - choose:
          - conditions:
              - condition: numeric_state
                entity_id: sensor.notification_priority
                above: 7
            sequence:
              - service: wled_effects.start_effect
                data:
                  effect_type: "breathe"
                  pulse_rate: 5.0  # Fast pulse
                  color: "255,0,0"  # Red
          - conditions:
              - condition: numeric_state
                entity_id: sensor.notification_priority
                below: 3
            sequence:
              - service: wled_effects.start_effect
                data:
                  effect_type: "sparkle"
                  density: 0.1  # Subtle
                  sparkle_color: "100,200,255"
```

### 2. System Health Dashboard
```yaml
# Use zones for multi-metric display
- name: "System Dashboard"
  effect_type: "meter"
  zone_count: 4
  zones:
    - # Zone 1: CPU
      state_entity: "sensor.processor_use"
      fill_mode: "bottom_up"
    - # Zone 2: Memory
      state_entity: "sensor.memory_use"
      fill_mode: "bottom_up"
    - # Zone 3: Disk
      state_entity: "sensor.disk_use"
      fill_mode: "bottom_up"
    - # Zone 4: Network
      state_entity: "sensor.network_throughput"
      fill_mode: "bottom_up"
```

### 3. Ambient Intelligence
```yaml
# Combine multiple effects with triggers
- name: "Smart Ambient"
  effect_type: "sparkle"
  state_entity: "sensor.home_activity_level"
  state_controls: "density"
  reactive_inputs:
    - entity_id: "binary_sensor.motion_detected"
      blend_mode: "add"
  triggers:
    - trigger_type: "state_change"
      entity_id: "binary_sensor.door_open"
      action: "burst"  # Sparkle burst on door open
```

---

## Performance Considerations

All effects are optimized for real-time operation:
- **Update rate**: 50ms (20 FPS) for smooth animations
- **State smoothing**: Built-in exponential smoothing prevents jittery visuals
- **Async operations**: Non-blocking state monitoring
- **Memory efficient**: Minimal state tracking per LED

## Compatibility

These effects leverage ALL generalized capabilities:
- ✅ StateSourceCoordinator for optional state input
- ✅ Data mapping with smoothing
- ✅ Trigger system integration
- ✅ Multi-zone support
- ✅ Reverse direction
- ✅ Blend modes
- ✅ Freeze on manual override
- ✅ Graceful fallback without state

## See Also

- [STATE_REACTIVE_EFFECTS.md](STATE_REACTIVE_EFFECTS.md) - Original effects with state support
- [CONTEXT_AWARE_FEATURES.md](CONTEXT_AWARE_FEATURES.md) - Base system capabilities
- [README.md](README.md) - Main integration documentation
