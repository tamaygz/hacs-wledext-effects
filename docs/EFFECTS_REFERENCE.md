# Effects Reference

Complete guide to all 9 built-in effects with configurations, examples, and use cases.

## Quick Navigation

- [Rainbow Wave](#rainbow-wave) - Flowing color animation
- [Segment Fade](#segment-fade) - Color transitions
- [Loading](#loading) - Progress bar animation
- [State Sync](#state-sync) - Data visualization
- [Breathe](#breathe) - Pulsing notification effect
- [Meter](#meter) - Gauge/bar chart visualization
- [Sparkle](#sparkle) - Twinkling activity indicator
- [Chase](#chase) - Moving scanner effect
- [Alert](#alert) - Multi-severity notification system

---

## Rainbow Wave

**Category**: Ambient / Decoration  
**Purpose**: Animated rainbow that flows across the LED strip  
**Best For**: Decoration, ambient lighting, color cycling

### Overview

Creates a smooth, flowing rainbow pattern that moves across your LED strip. The rainbow continuously animates, creating a mesmerizing effect perfect for ambient lighting.

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `wave_speed` | number | 10.0 | 1.0-100.0 | Animation speed (higher = faster) |
| `wave_length` | integer | 60 | 10-200 | Length of one complete rainbow cycle in LEDs |
| `brightness` | integer | 255 | 0-255 | Overall brightness |
| `reverse_direction` | boolean | false | - | Flip animation direction |

### State-Reactive Mode (Optional)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state_entity` | string | - | Entity ID to monitor |
| `state_controls` | string | "speed" | What to control: `speed`, `wavelength`, or `both` |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

### Examples

#### Basic Rainbow
```yaml
effect_type: rainbow_wave
config:
  wave_speed: 10.0
  wave_length: 60
  brightness: 200
```

#### Fast Rainbow
```yaml
effect_type: rainbow_wave
config:
  wave_speed: 50.0
  wave_length: 40
  reverse_direction: true
```

#### Temperature-Controlled Speed
```yaml
effect_type: rainbow_wave
config:
  wave_speed: 10.0
  wave_length: 60
  state_entity: sensor.room_temperature
  state_controls: speed
  state_min: 18.0
  state_max: 28.0
  # Warmer room = faster rainbow
```

### Use Cases

- **Ambient lighting**: Continuous decoration effect
- **Party mode**: Fast, vibrant rainbow
- **Calming display**: Slow, stretched rainbow
- **Temperature indicator**: Speed reflects temperature

---

## Segment Fade

**Category**: Ambient / Transition  
**Purpose**: Smooth color transitions between multiple colors  
**Best For**: Mood lighting, color transitions, gradients

### Overview

Smoothly transitions between two or more colors, creating a calming fade effect. Perfect for mood lighting and ambient environments.

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `color1` | string | "255,0,0" | R,G,B | First color (red) |
| `color2` | string | "0,0,255" | R,G,B | Second color (blue) |
| `transition_speed` | number | 2.0 | 0.1-10.0 | Transition speed (cycles per second) |
| `brightness` | integer | 255 | 0-255 | Overall brightness |
| `reverse_direction` | boolean | false | - | Reverse fade direction |

### State-Reactive Mode (Optional)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state_entity` | string | - | Entity ID to monitor |
| `state_controls` | string | "speed" | Control: `speed` or `position` |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

**Note**: When using `position` mode, state directly controls color position (0% = color1, 100% = color2).

### Examples

#### Red to Blue Fade
```yaml
effect_type: segment_fade
config:
  color1: "255,0,0"
  color2: "0,0,255"
  transition_speed: 1.0
```

#### Multi-Color Sunset
```yaml
effect_type: segment_fade
config:
  color1: "255,100,0"   # Orange
  color2: "100,0,100"   # Purple
  transition_speed: 0.5  # Slow
```

#### Brightness-Controlled Color
```yaml
effect_type: segment_fade
config:
  color1: "0,0,255"     # Blue (dim)
  color2: "255,255,0"   # Yellow (bright)
  state_entity: sensor.ambient_light
  state_controls: position
  state_min: 0
  state_max: 1000
  # Room brightness controls color
```

### Use Cases

- **Mood lighting**: Calming color transitions
- **Circadian rhythm**: Warm to cool colors
- **Status indication**: Color represents system state
- **Color picker**: Use `position` mode for precise color control

---

## Loading

**Category**: Animation / Progress  
**Purpose**: Moving bar with trail effects  
**Best For**: Progress indicators, animations, movement

### Overview

Creates a moving bar that travels across the LED strip with optional trailing fade. Perfect for progress indicators and dynamic animations.

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `color` | string | "0,255,0" | R,G,B | Bar color |
| `bar_size` | integer | 10 | 1-50 | Size of the moving bar in LEDs |
| `speed` | number | 0.05 | 0.01-1.0 | Movement speed (seconds per step) |
| `trail_fade` | boolean | true | - | Enable trailing fade effect |
| `brightness` | integer | 255 | 0-255 | Overall brightness |
| `reverse_direction` | boolean | false | - | Flip movement direction |

### State-Reactive Mode (Optional)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state_entity` | string | - | Entity ID to monitor |
| `state_controls` | string | "speed" | Control: `speed`, `position`, or `bar_size` |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

**Note**: When using `position` mode, bar stays at the position representing state value.

### Examples

#### Auto-Moving Bar
```yaml
effect_type: loading
config:
  color: "0,255,0"
  bar_size: 10
  speed: 0.05
  trail_fade: true
```

#### CPU Usage Bar
```yaml
effect_type: loading
config:
  color: "255,100,0"
  bar_size: 5
  state_entity: sensor.processor_use
  state_controls: position
  state_min: 0
  state_max: 100
  # Bar position shows CPU usage
```

#### Download Progress
```yaml
effect_type: loading
config:
  color: "0,255,255"
  bar_size: 15
  state_entity: sensor.download_percentage
  state_controls: position
  state_min: 0
  state_max: 100
  trail_fade: true
```

### Use Cases

- **Progress bars**: Show download/upload progress
- **Resource monitoring**: CPU, memory, disk usage
- **Timers**: Visual countdown/countup
- **Animations**: Continuous moving effect

---

## State Sync

**Category**: Data Visualization  
**Purpose**: Advanced state visualization with multiple modes  
**Best For**: Sensor monitoring, metrics display, smart home status

### Overview

The most versatile visualization effect. Displays Home Assistant entity states with multiple animation modes, color gradients, and multi-input support.

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `state_entity` | string | **Required** | - | Entity ID to visualize |
| `state_attribute` | string | - | - | Optional: specific attribute |
| `min_value` | number | 0.0 | - | Minimum expected state value |
| `max_value` | number | 100.0 | - | Maximum expected state value |
| `animation_mode` | string | "fill" | - | See modes below |
| `color_low` | string | "0,255,0" | R,G,B | Color at minimum value (green) |
| `color_high` | string | "255,0,0" | R,G,B | Color at maximum value (red) |
| `transition_mode` | string | "smooth" | - | `instant`, `fade`, or `smooth` |
| `reverse_direction` | boolean | false | - | Flip LED order |
| `freeze_on_manual` | boolean | false | - | Pause on manual WLED control |

### Animation Modes

| Mode | Description | Visual |
|------|-------------|--------|
| `fill` | Fills from start based on value | `[■][■][■][□][□]` |
| `center` | Expands from center outward | `[□][■][■][■][□]` |
| `dual` | Fills from both ends inward | `[■][□][□][□][■]` |
| `solid` | All LEDs same color | `[■][■][■][■][■]` |

### Multi-Input Support

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `reactive_inputs` | list | - | Additional entity IDs to monitor |
| `blend_mode` | string | "average" | How to combine: `average`, `max`, `min`, `multiply`, `add` |

### Examples

#### Temperature Visualization
```yaml
effect_type: state_sync
config:
  state_entity: sensor.living_room_temperature
  min_value: 15
  max_value: 30
  animation_mode: fill
  color_low: "0,0,255"    # Blue (cold)
  color_high: "255,0,0"   # Red (hot)
  transition_mode: smooth
```

#### Battery Level
```yaml
effect_type: state_sync
config:
  state_entity: sensor.phone_battery
  min_value: 0
  max_value: 100
  animation_mode: fill
  color_low: "255,0,0"    # Red (low)
  color_high: "0,255,0"   # Green (full)
```

#### Multi-Sensor Ambient
```yaml
effect_type: state_sync
config:
  state_entity: sensor.ambient_light
  reactive_inputs:
    - sensor.ambient_light
    - sensor.motion_activity
    - sensor.circadian_brightness
  blend_mode: max
  animation_mode: solid
  transition_mode: smooth
  freeze_on_manual: true
```

### Use Cases

- **Temperature monitoring**: Color-coded temperature display
- **Resource monitoring**: CPU, memory, network usage
- **Battery display**: Phone, laptop, device batteries
- **Ambient intelligence**: Multi-sensor responsive lighting
- **Security status**: Visual system state indicator

---

## Breathe

**Category**: Notification / Ambient  
**Purpose**: Smooth pulsing pattern  
**Best For**: Gentle notifications, alerts, status indicators, meditation

### Overview

Creates a calming breathing or pulsing effect using sine wave brightness modulation. Perfect for notifications that need attention without being jarring.

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `color` | string | "0,100,255" | R,G,B | LED color |
| `pulse_rate` | number | 1.0 | 0.1-10.0 | Breathing rate (cycles/second) |
| `min_brightness` | integer | 10 | 0-255 | Minimum brightness |
| `max_brightness` | integer | 255 | 0-255 | Maximum brightness |
| `easing` | string | "sine" | - | Easing function: `sine`, `linear`, `ease_in_out` |

### State-Reactive Mode (Optional)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state_entity` | string | - | Entity ID to monitor |
| `state_controls` | string | "rate" | Control: `rate`, `intensity`, or `both` |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

### Examples

#### Calming Breathe
```yaml
effect_type: breathe
config:
  color: "0,50,150"     # Dim blue
  pulse_rate: 0.2       # 12 breaths per minute
  min_brightness: 5
  max_brightness: 50
```

#### Notification Urgency
```yaml
effect_type: breathe
config:
  color: "255,100,0"    # Orange
  pulse_rate: 1.0
  state_entity: sensor.notification_priority
  state_controls: rate
  state_min: 0
  state_max: 10
  # Higher priority = faster pulse
```

#### System Load Indicator
```yaml
effect_type: breathe
config:
  color: "100,200,255"
  pulse_rate: 1.0
  state_entity: sensor.cpu_usage
  state_controls: intensity
  state_min: 0
  state_max: 100
  # Higher CPU = brighter pulse
```

### Use Cases

- **Gentle notifications**: Non-intrusive alerts
- **Status indicators**: System load, activity level
- **Meditation timer**: Breathing guide
- **Sleep aid**: Slow, calming pulse
- **Priority indication**: Pulse rate shows urgency

---

## Meter

**Category**: Data Visualization  
**Purpose**: Gauge/bar chart with threshold colors  
**Best For**: CPU, battery, temperature, progress tracking

### Overview

Visualizes numeric values as a filling bar with automatic color changes based on threshold ranges. Perfect for any metric that has "low/medium/high" states.

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `fill_mode` | string | "bottom_up" | - | See modes below |
| `default_level` | number | 50.0 | 0-100 | Level when no state |
| `color_low` | string | "0,255,0" | R,G,B | Color for low values (green) |
| `color_medium` | string | "255,255,0" | R,G,B | Color for medium values (yellow) |
| `color_high` | string | "255,0,0" | R,G,B | Color for high values (red) |
| `threshold_medium` | number | 50.0 | 0-100 | Threshold for medium color |
| `threshold_high` | number | 80.0 | 0-100 | Threshold for high color |
| `show_peak` | boolean | false | - | Show peak level indicator (white) |
| `background_color` | string | "10,10,10" | R,G,B | Background for unfilled area |

### Fill Modes

| Mode | Description | Visual |
|------|-------------|--------|
| `bottom_up` | Fills from bottom to top | Standard bar chart |
| `center_out` | Expands from center | Symmetric gauge |
| `bidirectional` | Fills from both ends | Dual gauge |

### State-Reactive Mode

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state_entity` | string | - | Entity ID to visualize |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

### Examples

#### CPU Usage Meter
```yaml
effect_type: meter
config:
  fill_mode: bottom_up
  state_entity: sensor.processor_use
  state_min: 0
  state_max: 100
  threshold_medium: 60
  threshold_high: 85
  show_peak: true
  # Green <60%, yellow 60-85%, red >85%
```

#### Battery Gauge
```yaml
effect_type: meter
config:
  fill_mode: bottom_up
  state_entity: sensor.phone_battery
  color_low: "255,0,0"      # Red for low battery
  color_medium: "255,165,0" # Orange for medium
  color_high: "0,255,0"     # Green for high
  threshold_medium: 30
  threshold_high: 70
```

#### Temperature Gauge
```yaml
effect_type: meter
config:
  fill_mode: center_out     # Emanate from center
  state_entity: sensor.living_room_temperature
  state_min: 15
  state_max: 30
  color_low: "0,0,255"      # Cold = blue
  color_medium: "0,255,0"   # Comfortable = green
  color_high: "255,0,0"     # Hot = red
  threshold_medium: 20
  threshold_high: 26
```

### Use Cases

- **Resource monitoring**: CPU, memory, disk usage
- **Battery levels**: Phone, laptop, devices
- **Temperature display**: Room, server, outdoor
- **Signal strength**: WiFi, cellular
- **Progress tracking**: Downloads, uploads, tasks

---

## Sparkle

**Category**: Activity / Ambient  
**Purpose**: Twinkling starfield effect  
**Best For**: Activity indicators, notification counters, ambient effects

### Overview

Creates a twinkling starfield where random pixels light up and fade out. Density and speed can represent activity levels or notification counts.

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `sparkle_color` | string | "255,255,255" | R,G,B | Sparkle color (white) |
| `background_color` | string | "0,0,20" | R,G,B | Background color |
| `density` | number | 0.1 | 0.0-1.0 | Sparkle density (probability) |
| `fade_rate` | number | 0.8 | 0.0-1.0 | Fade speed (higher = slower fade) |
| `color_variation` | boolean | false | - | Enable random hue variation |

### State-Reactive Mode (Optional)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state_entity` | string | - | Entity ID to monitor |
| `state_controls` | string | "density" | Control: `density`, `speed`, or `both` |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

### Examples

#### Static Starfield
```yaml
effect_type: sparkle
config:
  sparkle_color: "200,200,255"
  background_color: "0,0,30"
  density: 0.05         # Sparse
  fade_rate: 0.95       # Slow fade
  color_variation: true
```

#### Network Activity Indicator
```yaml
effect_type: sparkle
config:
  sparkle_color: "0,255,255"    # Cyan
  state_entity: sensor.network_throughput_mb
  state_controls: density
  state_min: 0
  state_max: 100
  # More traffic = more sparkles
```

#### Notification Counter
```yaml
effect_type: sparkle
config:
  sparkle_color: "255,100,200"  # Pink
  state_entity: sensor.unread_message_count
  state_controls: both
  state_min: 0
  state_max: 50
  color_variation: true
  # More messages = more frequent, faster sparkles
```

### Use Cases

- **Network activity**: Visual network traffic indicator
- **Message counters**: Unread emails, notifications
- **System activity**: Background process indicator
- **Ambient decoration**: Starfield effect
- **Smart home activity**: Number of active devices

---

## Chase

**Category**: Animation / Status  
**Purpose**: Moving scanner or chase pattern  
**Best For**: Processing indicators, directional effects, classic animations

### Overview

Creates a Knight Rider / Cylon style scanner effect or chase pattern. A group of LEDs moves along the strip with optional fade trail.

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `chase_color` | string | "255,100,0" | R,G,B | Chase color (orange) |
| `background_color` | string | "0,0,0" | R,G,B | Background color |
| `chase_length` | integer | 5 | 1-50 | Length of chase in LEDs |
| `speed` | number | 0.05 | 0.001-0.5 | Movement speed (delay between steps) |
| `fade_tail` | boolean | true | - | Fade the tail of the chase |
| `bounce` | boolean | true | - | Bounce at ends vs wrap around |
| `scan_mode` | boolean | false | - | Scanner mode (Cylon/KITT style) |

### State-Reactive Mode (Optional)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state_entity` | string | - | Entity ID to monitor |
| `state_controls` | string | "speed" | Control: `speed`, `direction`, `length`, or `both` |
| `state_min` | number | 0.0 | Minimum state value |
| `state_max` | number | 100.0 | Maximum state value |

### Examples

#### Classic KITT Scanner
```yaml
effect_type: chase
config:
  chase_color: "255,0,0"
  scan_mode: true
  chase_length: 10
  bounce: true
  speed: 0.03
  fade_tail: true
```

#### Processing Indicator
```yaml
effect_type: chase
config:
  chase_color: "0,255,100"
  chase_length: 8
  state_entity: sensor.processing_queue_length
  state_controls: speed
  state_min: 0
  state_max: 100
  # More items in queue = faster chase
```

#### Download Progress Chase
```yaml
effect_type: chase
config:
  chase_color: "0,255,0"
  state_entity: sensor.download_percentage
  state_controls: length
  state_min: 0
  state_max: 100
  bounce: false
  # Chase grows with progress
```

### Use Cases

- **Processing indicators**: Data processing, queue status
- **Classic effects**: KITT/Cylon scanner
- **Directional flow**: Data transfer direction
- **Progress indication**: Growing chase bar
- **Retro displays**: 80s style animations

---

## Alert

**Category**: Notification / Alert  
**Purpose**: Multi-severity notification system  
**Best For**: Security alerts, warnings, critical notifications

### Overview

The most attention-grabbing effect. Features 5 severity levels, 8 flash patterns, auto-escalation, acknowledgment support, and customizable behaviors.

### Severity Levels

| Severity | Default Color | Flash Rate | Pattern | Use Case |
|----------|---------------|------------|---------|----------|
| **debug** | Dim Blue | 0.5 Hz | Blink | Development, testing |
| **info** | Cyan/Blue | 1.0 Hz | Pulse | Information, updates |
| **warning** | Yellow/Amber | 2.0 Hz | Double Pulse | Caution, warnings |
| **alert** | Orange | 3.0 Hz | Triple Pulse | Urgent attention |
| **critical** | Red + White | 6.0 Hz | Strobe | Emergency, critical errors |

### Flash Patterns

1. **steady** - Persistent solid color
2. **blink** - Simple on/off flashing
3. **pulse** - Smooth sine wave fade
4. **double_pulse** - Two quick flashes
5. **triple_pulse** - Three quick flashes
6. **strobe** - Rapid bright flashes
7. **sparkle_burst** - Explosive sparkle effect
8. **auto** - Uses severity default

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `severity` | string | "info" | Severity level (see above) or `auto` |
| `pattern` | string | "auto" | Flash pattern (see above) |
| `flash_rate` | number | 0.0 | Custom flash rate (0 = use default) |
| `duty_cycle` | number | 0.5 | On-time percentage (0.1-0.9) |
| `color` | string | "auto" | Custom color or `auto` |
| `secondary_color` | string | "255,255,255" | Secondary color for patterns |
| `affected_area` | string | "full" | Area: `full`, `center`, `edges`, `random` |
| `sparkle_count` | integer | 50 | Number of sparkles (10-200) |
| `sparkle_decay` | number | 0.85 | Sparkle fade rate (0.5-0.98) |

### Advanced Features

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `escalate_after` | number | 0.0 | Seconds before escalating (0 = disabled) |
| `max_duration` | number | 0.0 | Auto-stop seconds (0 = infinite) |
| `acknowledge_entity` | string | - | Entity for acknowledgment |
| `state_entity` | string | - | Entity for auto-severity |
| `severity_thresholds` | object | {...} | Value → severity mapping |

### Examples

#### Simple Info Alert
```yaml
effect_type: alert
config:
  severity: info
  # Defaults: cyan, 1 Hz pulse
```

#### Critical Security Alert
```yaml
effect_type: alert
config:
  severity: critical
  pattern: strobe
  color: "255,0,0"
  max_duration: 300
  acknowledge_entity: input_boolean.security_ack
```

#### Auto-Severity from CPU
```yaml
effect_type: alert
config:
  severity: auto
  state_entity: sensor.processor_use
  severity_thresholds:
    debug: 20
    info: 40
    warning: 70
    alert: 90
  # Pattern auto-adjusts with CPU load
```

#### Escalating Alert
```yaml
effect_type: alert
config:
  severity: info
  pattern: pulse
  escalate_after: 60
  max_duration: 600
  acknowledge_entity: input_boolean.alert_ack
  # Escalates every minute if not acknowledged
```

### Use Cases

- **Security system**: Alarm states, intrusion alerts
- **System monitoring**: Server errors, resource alerts
- **Smart home notifications**: Priority-based alerts
- **Door/window status**: Left open warnings
- **Timer completion**: Laundry, cooking, tasks
- **Emergency notifications**: Critical system failures

---

## Comparison Table

| Effect | Category | Attention Level | CPU Load | State-Driven |
|--------|----------|-----------------|----------|--------------|
| **Rainbow Wave** | Ambient | Low | Low | Optional |
| **Segment Fade** | Ambient | Low | Low | Optional |
| **Loading** | Animation | Medium | Low | Optional |
| **State Sync** | Visualization | Low-Med | Low-Med | Required |
| **Breathe** | Notification | Medium | Low | Optional |
| **Meter** | Visualization | Medium | Low | Optional |
| **Sparkle** | Activity | Low-Med | Medium | Optional |
| **Chase** | Animation | Medium | Low | Optional |
| **Alert** | Notification | High | Low-Med | Optional |

---

## Effect Selection Guide

### By Purpose

**Decoration / Ambient**:
- Rainbow Wave (flowing colors)
- Segment Fade (color transitions)
- Sparkle (starfield)

**Data Visualization**:
- State Sync (multi-mode display)
- Meter (gauges, bars)
- Loading (progress bars)

**Notifications / Alerts**:
- Alert (multi-severity, most configurable)
- Breathe (gentle notifications)
- Sparkle (activity burst)

**Status Indicators**:
- Meter (levels, percentages)
- Breathe (intensity levels)
- Chase (processing state)

**Activity / Processing**:
- Chase (directional flow)
- Sparkle (random activity)
- Loading (movement)

### By Data Type

- **Percentage (0-100)**: Meter, State Sync, Loading (position mode)
- **Temperature**: State Sync, Meter (with thresholds)
- **Binary (on/off)**: Breathe, Alert, Sparkle (burst)
- **Count/Activity**: Sparkle (density), Chase (speed)
- **Priority/Severity**: Alert (auto-severity), Breathe (rate)

---

## Next Steps

- **[Context-Aware Features](CONTEXT_AWARE_FEATURES.md)** - Advanced multi-input, triggers, zones
- **[Advanced Guide](ADVANCED_GUIDE.md)** - Complex automations and optimizations
- **[Effect Development](EFFECT_DEVELOPMENT.md)** - Create your own custom effects

---

**Last Updated**: January 2026  
**Version**: 1.0.0
