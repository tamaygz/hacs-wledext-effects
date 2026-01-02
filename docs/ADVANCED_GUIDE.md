# Advanced Guide

Advanced features, automations, and optimization techniques for WLED Effects.

## Table of Contents

- [Trigger System](#trigger-system)
- [Data Mapping](#data-mapping)
- [Multi-Input Blending](#multi-input-blending)
- [Effect Chaining](#effect-chaining)
- [Dynamic Configuration](#dynamic-configuration)
- [Automation Integration](#automation-integration)
- [Performance Optimization](#performance-optimization)
- [Multi-Device Setup](#multi-device-setup)

---

## Trigger System

The trigger system allows effects to respond to specific events, not just continuous state changes.

### Trigger Types

#### 1. State Change Trigger

Fires when an entity state changes.

```yaml
trigger_config:
  trigger_type: state_change
  entity_id: binary_sensor.motion_detected
  from_state: 'off'  # Optional: specific from state
  to_state: 'on'     # Optional: specific to state
```

**Use Case**: Change effect when motion detected.

#### 2. Threshold Trigger

Fires when a numeric value crosses a threshold.

```yaml
trigger_config:
  trigger_type: threshold
  entity_id: sensor.temperature
  threshold: 25.0
  comparison: ">"    # Options: >, <, >=, <=, ==, !=
```

**Use Case**: Alert when temperature exceeds limit.

#### 3. Time Trigger

Fires at specific times.

```yaml
trigger_config:
  trigger_type: time
  time_pattern: "18:00"  # HH:MM format
```

**Use Case**: Change lighting at sunset.

#### 4. Event Trigger

Fires on Home Assistant events.

```yaml
trigger_config:
  trigger_type: event
  event_type: custom_event
  event_data:
    action: "alert"
```

**Use Case**: Respond to custom automations.

### Implementing Triggers

In your effect configuration:

```yaml
effect_type: breathe
config:
  color: "0,100,255"
  pulse_rate: 1.0
  trigger_config:
    trigger_type: state_change
    entity_id: binary_sensor.doorbell
    to_state: 'on'
  # When doorbell pressed, trigger callback
```

### Multiple Triggers

```yaml
triggers:
  - trigger_type: threshold
    entity_id: sensor.cpu_temp
    threshold: 70
    comparison: ">"
  - trigger_type: time
    time_pattern: "22:00"
  - trigger_type: state_change
    entity_id: binary_sensor.alert
```

---

## Data Mapping

Transform input values to effect parameters with advanced interpolation.

### Basic Mapping

Map sensor range to effect parameter range:

```yaml
state_entity: sensor.temperature
state_min: 15    # Input minimum
state_max: 30    # Input maximum
# Effect maps this to its parameter range
```

### Interpolation Curves

Control how values are mapped:

| Curve | Description | Use Case |
|-------|-------------|----------|
| `linear` | Direct 1:1 mapping | Default, predictable |
| `ease_in` | Slow start, fast end | Gradual then dramatic |
| `ease_out` | Fast start, slow end | Dramatic then gradual |
| `ease_in_out` | Smooth both ends | Natural, organic feel |

```yaml
data_mapping:
  curve: ease_in_out
  # Smoother transitions at extremes
```

### Value Smoothing

Prevent jittery effects from noisy sensors:

```yaml
transition_mode: smooth
smoothing_factor: 0.2  # 0.0-1.0, lower = smoother
```

**How it works**: Exponential moving average filters rapid fluctuations.

### Custom Transformations

```python
# In custom effects
mapped_value = self.map_value(
    input_value,
    input_min=0.0,
    input_max=100.0,
    output_min=1.0,
    output_max=50.0,
    smooth=True
)
```

---

## Multi-Input Blending

Combine multiple sensors/entities to control a single effect.

### Blend Modes

| Mode | Formula | Use Case |
|------|---------|----------|
| `average` | (A + B + C) / 3 | Balanced combination |
| `max` | max(A, B, C) | Use highest value |
| `min` | min(A, B, C) | Use lowest value |
| `multiply` | A × B × C | Compound factors |
| `add` | A + B + C | Cumulative total |

### Example: Multi-Sensor Ambient Lighting

```yaml
effect_type: state_sync
config:
  state_entity: sensor.ambient_light
  reactive_inputs:
    - sensor.ambient_light      # Primary input
    - sensor.motion_activity    # Boost on activity
    - sensor.circadian_brightness  # Time-of-day adjustment
  blend_mode: multiply
  # All three factors affect final brightness
```

### Example: Maximum Sensor

```yaml
effect_type: meter
config:
  state_entity: sensor.cpu_temp
  reactive_inputs:
    - sensor.cpu_temp
    - sensor.gpu_temp
    - sensor.system_temp
  blend_mode: max
  # Show highest temperature
```

### Weighted Blending

```yaml
reactive_inputs:
  - entity_id: sensor.temperature
    weight: 0.5
  - entity_id: sensor.humidity
    weight: 0.3
  - entity_id: sensor.light
    weight: 0.2
blend_mode: weighted_average
```

---

## Effect Chaining

Run effects sequentially or conditionally.

### Sequential Effects

```yaml
automation:
  - alias: "Morning Sequence"
    trigger:
      - platform: time
        at: "07:00"
    action:
      # Phase 1: Gentle wake
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_breathe_morning
      - delay: "00:05:00"
      
      # Phase 2: Increase brightness
      - service: number.set_value
        target:
          entity_id: number.wled_effects_breathe_morning_brightness
        data:
          value: 200
      - delay: "00:05:00"
      
      # Phase 3: Switch to active
      - service: switch.turn_off
        target:
          entity_id: switch.wled_effects_breathe_morning
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_rainbow_day
```

### Conditional Effect Selection

```yaml
automation:
  - alias: "Adaptive Lighting"
    trigger:
      - platform: state
        entity_id: sensor.room_occupancy
    action:
      - choose:
          # Occupied
          - conditions:
              - condition: state
                entity_id: sensor.room_occupancy
                state: 'on'
            sequence:
              - service: switch.turn_on
                target:
                  entity_id: >
                    {% if is_state('sun.sun', 'above_horizon') %}
                      switch.wled_effects_bright_ambient
                    {% else %}
                      switch.wled_effects_warm_evening
                    {% endif %}
          
          # Unoccupied
          - conditions:
              - condition: state
                entity_id: sensor.room_occupancy
                state: 'off'
            sequence:
              - service: switch.turn_on
                target:
                  entity_id: switch.wled_effects_dim_standby
```

---

## Dynamic Configuration

Update effect parameters on-the-fly without restarting.

### Using Number Entities

```yaml
service: number.set_value
target:
  entity_id: number.wled_effects_rainbow_wave_speed
data:
  value: 50  # Double the speed
```

### Using Select Entities

```yaml
service: select.select_option
target:
  entity_id: select.wled_effects_state_sync_animation_mode
data:
  option: "center"  # Change animation mode
```

### Automation-Driven Configuration

```yaml
automation:
  - alias: "Adaptive Effect Speed"
    trigger:
      - platform: state
        entity_id: sensor.home_activity_level
    action:
      - service: number.set_value
        target:
          entity_id: number.wled_effects_sparkle_density
        data:
          value: >
            {{ states('sensor.home_activity_level') | float / 100 }}
```

---

## Automation Integration

### Pattern 1: Presence-Based Effects

```yaml
automation:
  - alias: "Hallway Lighting"
    mode: restart
    trigger:
      - platform: state
        entity_id: binary_sensor.hallway_motion
        to: 'on'
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_loading_path
      - wait_for_trigger:
          - platform: state
            entity_id: binary_sensor.hallway_motion
            to: 'off'
            for: "00:01:00"
      - service: switch.turn_off
        target:
          entity_id: switch.wled_effects_loading_path
```

### Pattern 2: Alert Escalation

```yaml
automation:
  - alias: "Temperature Alert Escalation"
    trigger:
      - platform: numeric_state
        entity_id: sensor.server_temperature
        above: 70
    action:
      # Level 1: Warning
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_alert_warning
      - wait_template: "{{ states('sensor.server_temperature') | float < 70 }}"
        timeout: "00:05:00"
        continue_on_timeout: true
      
      # Level 2: Critical (if still high)
      - condition: numeric_state
        entity_id: sensor.server_temperature
        above: 70
      - service: switch.turn_off
        target:
          entity_id: switch.wled_effects_alert_warning
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_alert_critical
```

### Pattern 3: Multi-Zone Control

```yaml
automation:
  - alias: "Security Zones"
    trigger:
      - platform: state
        entity_id:
          - binary_sensor.front_door
          - binary_sensor.back_door
          - binary_sensor.window_1
          - binary_sensor.window_2
        to: 'on'
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_alert_security
      - service: select.select_option
        target:
          entity_id: select.wled_effects_alert_security_zone
        data:
          option: >
            {% if trigger.entity_id == 'binary_sensor.front_door' %}
              zone_0
            {% elif trigger.entity_id == 'binary_sensor.back_door' %}
              zone_1
            {% else %}
              zone_2
            {% endif %}
```

---

## Performance Optimization

### Best Practices

#### 1. Update Rate Management

Default update rate is 50ms (20 FPS). For most effects, this is optimal.

```python
# In custom effects
async def run_effect(self):
    while self.running:
        # ... effect logic ...
        await asyncio.sleep(0.05)  # 20 FPS
```

For slower effects (e.g., breathe):
```python
await asyncio.sleep(0.1)  # 10 FPS sufficient
```

#### 2. State Monitoring Efficiency

Use `transition_mode: smooth` to reduce API calls:

```yaml
transition_mode: smooth
# Smooths values internally, fewer WLED updates
```

#### 3. LED Count Optimization

Effects scale well up to 300 LEDs. Beyond that:
- Use zones to divide processing
- Increase update interval slightly
- Consider simpler effects for large strips

#### 4. Network Optimization

**Connection Pooling**: WLED Effects automatically pools connections.

**Rate Limiting**: Built-in rate limiter prevents overwhelming WLED devices.

**Circuit Breaker**: Auto-disables effects on repeated failures, prevents cascading issues.

### Monitoring Performance

Check sensor entities:

```yaml
sensor.wled_effects_<name>_frame_rate  # Current FPS
sensor.wled_effects_<name>_latency     # Network latency
sensor.wled_effects_<name>_error_rate  # Error percentage
```

### Troubleshooting Slow Performance

**Symptoms**: Laggy animations, low frame rate

**Solutions**:
1. Reduce `state_min` / `state_max` update frequency
2. Increase effect update interval
3. Simplify effect (fewer LEDs, simpler calculations)
4. Check network latency to WLED device
5. Verify WLED device isn't overloaded

---

## Multi-Device Setup

Manage multiple WLED devices with coordinated effects.

### Independent Devices

Each effect configuration targets one device:

```yaml
# Device 1: Kitchen strip
- name: "Kitchen Rainbow"
  wled_host: "192.168.1.10"
  effect_type: "rainbow_wave"

# Device 2: Bedroom strip
- name: "Bedroom Breathe"
  wled_host: "192.168.1.11"
  effect_type: "breathe"
```

### Synchronized Effects

Same effect on multiple devices:

```yaml
automation:
  - alias: "All Lights Rainbow"
    action:
      - service: switch.turn_on
        target:
          entity_id:
            - switch.wled_effects_kitchen_rainbow
            - switch.wled_effects_bedroom_rainbow
            - switch.wled_effects_hallway_rainbow
```

### Coordinated Effects

Different effects that work together:

```yaml
automation:
  - alias: "Security Alert All Zones"
    action:
      # Front: Red strobe
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_front_alert_critical
      
      # Back: Orange pulse
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_back_alert_warning
      
      # Interior: Blue steady
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_interior_alert_info
```

### Room-Based Groups

```yaml
# groups.yaml
wled_effects_living_room:
  name: "Living Room LED Effects"
  entities:
    - switch.wled_effects_tv_backlight
    - switch.wled_effects_shelf_accent
    - switch.wled_effects_ceiling_ambient

# Automation
automation:
  - alias: "Movie Mode"
    action:
      - service: homeassistant.turn_off
        target:
          entity_id: group.wled_effects_living_room
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_tv_backlight_dim
```

---

## Advanced Recipes

### Recipe 1: Adaptive Home Lighting

```yaml
effect_type: state_sync
config:
  state_entity: sensor.adaptive_brightness
  reactive_inputs:
    - sensor.ambient_light         # Outdoor light level
    - sensor.circadian_brightness  # Time of day
    - binary_sensor.home_occupied  # Presence
  blend_mode: multiply
  transition_mode: smooth
  freeze_on_manual: true
  animation_mode: solid
  color_low: "255,200,150"    # Warm
  color_high: "255,255,255"   # Bright white
```

### Recipe 2: Smart Notification System

```yaml
# Low priority: Sparkle
- name: "Notifications Low"
  effect_type: sparkle
  density: 0.1
  sparkle_color: "100,200,255"

# Medium priority: Breathe
- name: "Notifications Medium"
  effect_type: breathe
  pulse_rate: 1.0
  color: "255,200,0"

# High priority: Alert
- name: "Notifications High"
  effect_type: alert
  severity: alert
  pattern: triple_pulse

# Automation to switch
automation:
  - alias: "Smart Notifications"
    trigger:
      - platform: state
        entity_id: sensor.notification_priority
    action:
      - service: switch.turn_on
        target:
          entity_id: >
            {% if states('sensor.notification_priority') | int < 3 %}
              switch.wled_effects_notifications_low
            {% elif states('sensor.notification_priority') | int < 7 %}
              switch.wled_effects_notifications_medium
            {% else %}
              switch.wled_effects_notifications_high
            {% endif %}
```

### Recipe 3: Weather-Reactive Display

```yaml
automation:
  - alias: "Weather Display"
    trigger:
      - platform: state
        entity_id: weather.home
    action:
      - service: switch.turn_on
        target:
          entity_id: >
            {% set condition = states('weather.home') %}
            {% if condition == 'sunny' %}
              switch.wled_effects_weather_sunny
            {% elif condition == 'rainy' %}
              switch.wled_effects_weather_rainy
            {% elif condition == 'cloudy' %}
              switch.wled_effects_weather_cloudy
            {% elif condition == 'snowy' %}
              switch.wled_effects_weather_snowy
            {% else %}
              switch.wled_effects_weather_default
            {% endif %}

# Effect configurations
- name: "Weather Sunny"
  effect_type: rainbow_wave
  wave_speed: 15
  
- name: "Weather Rainy"
  effect_type: loading
  color: "0,100,200"
  speed: 0.1
  
- name: "Weather Cloudy"
  effect_type: segment_fade
  color1: "100,100,100"
  color2: "150,150,150"
  
- name: "Weather Snowy"
  effect_type: sparkle
  sparkle_color: "255,255,255"
  density: 0.3
```

---

## See Also

- **[Context-Aware Features](CONTEXT_AWARE_FEATURES.md)** - Base system capabilities
- **[Effects Reference](EFFECTS_REFERENCE.md)** - All effects documentation
- **[Effect Development](EFFECT_DEVELOPMENT.md)** - Create custom effects
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues

---

**Last Updated**: January 2026  
**Version**: 1.0.0
