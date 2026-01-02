# Alert Effect - Comprehensive Notification System

## Overview

The **Alert Effect** is a highly configurable notification system designed to grab attention and communicate urgency through LED patterns. Unlike the calming Breathe effect, Alert is specifically engineered for **notifications, warnings, and critical alerts** that require immediate attention.

## Key Features

### 🎚️ Severity Levels
Automatic severity-based defaults with industry-standard color coding:

| Severity | Default Color | Flash Rate | Pattern | Use Case |
|----------|---------------|------------|---------|----------|
| **Debug** | Dim Blue | 0.5 Hz | Blink | Development, testing |
| **Info** | Cyan/Blue | 1.0 Hz | Pulse | Information, updates |
| **Warning** | Yellow/Amber | 2.0 Hz | Double Pulse | Caution, non-critical warnings |
| **Alert** | Orange | 3.0 Hz | Triple Pulse | Urgent attention needed |
| **Critical** | Red + White | 6.0 Hz | Strobe | Emergency, critical errors |

### 🎭 Flash Patterns

Eight distinct patterns for different notification needs:

1. **Steady** - Persistent solid color (ongoing status)
2. **Blink** - Simple on/off flashing
3. **Pulse** - Smooth sine wave fade (less jarring)
4. **Double Pulse** - Two quick flashes (moderate urgency)
5. **Triple Pulse** - Three quick flashes (high urgency)
6. **Strobe** - Rapid bright flashes (maximum attention)
7. **Sparkle Burst** - Explosive sparkle effect (dramatic alerts)
8. **Auto** - Uses severity default pattern

### 🎨 Customization Options

- **Colors**: Custom primary/secondary colors or auto (severity defaults)
- **Flash Rate**: 0.5-10 Hz (overrides severity default)
- **Duty Cycle**: On-time percentage for blink patterns
- **Affected Area**: Full strip, center, edges, or random LEDs
- **Sparkle Count**: 10-200 sparkles for burst pattern
- **Decay Rate**: How fast sparkles fade

### 🚀 Advanced Features

#### 1. Auto-Severity from State
Map entity values to severity levels automatically:

```yaml
state_entity: sensor.system_load
severity: auto
severity_thresholds:
  debug: 10    # Below 10% = debug
  info: 30     # 10-30% = info
  warning: 60  # 30-60% = warning
  alert: 85    # 60-85% = alert
  # Above 85% = critical
```

#### 2. Acknowledgment Support
Alert stops when acknowledged:

```yaml
acknowledge_entity: input_boolean.alert_acknowledged
# Set to 'on' to stop alert
```

#### 3. Auto-Escalation
Automatically increase severity over time:

```yaml
severity: info
escalate_after: 30  # Escalate every 30 seconds
# info → warning → alert → critical
```

#### 4. Max Duration
Auto-stop after specified time:

```yaml
max_duration: 120  # Stop after 2 minutes
```

#### 5. Targeted Areas
Control which LEDs flash:

```yaml
affected_area: center  # Only center LEDs
# Options: full, center, edges, random
```

---

## Configuration Examples

### 1. Simple Info Notification
```yaml
service: wled_effects.start_effect
data:
  effect_name: alert
  config:
    severity: info
    # Uses defaults: cyan, 1 Hz, pulse pattern
```

### 2. Critical Security Alert
```yaml
service: wled_effects.start_effect
data:
  effect_name: alert
  config:
    severity: critical
    pattern: strobe
    color: "255,0,0"          # Red
    secondary_color: "255,255,255"  # White flashes
    affected_area: full
    max_duration: 300          # 5 minutes
    acknowledge_entity: input_boolean.security_acknowledged
```

### 3. Custom Warning Pattern
```yaml
service: wled_effects.start_effect
data:
  effect_name: alert
  config:
    severity: warning
    pattern: double_pulse
    flash_rate: 2.5           # Custom rate
    color: "255,150,0"        # Custom orange
    affected_area: edges      # Only edge LEDs
```

### 4. Auto-Severity from CPU Load
```yaml
service: wled_effects.start_effect
data:
  effect_name: alert
  config:
    severity: auto
    state_entity: sensor.processor_use
    severity_thresholds:
      debug: 20
      info: 40
      warning: 70
      alert: 90
    # Pattern auto-adjusts with severity
```

### 5. Escalating Home Alert
```yaml
service: wled_effects.start_effect
data:
  effect_name: alert
  config:
    severity: info
    pattern: pulse
    escalate_after: 60        # Escalate every minute
    max_duration: 600         # Stop after 10 minutes
    acknowledge_entity: input_boolean.home_alert_ack
    # Starts gentle, gets more urgent if not acknowledged
```

### 6. Dramatic Sparkle Burst
```yaml
service: wled_effects.start_effect
data:
  effect_name: alert
  config:
    severity: alert
    pattern: sparkle_burst
    color: "255,0,255"        # Magenta
    sparkle_count: 100        # Many sparkles
    sparkle_decay: 0.9        # Slow fade
    affected_area: random
```

### 7. Multi-Zone Alert System
```yaml
service: wled_effects.start_effect
data:
  effect_name: alert
  config:
    severity: warning
    zone_count: 3
    # Zone 1: Front door alert
    # Zone 2: Window alert
    # Zone 3: Motion alert
```

---

## Use Case Patterns

### Security System Integration

```yaml
automation:
  - alias: "Security Alert Levels"
    trigger:
      - platform: state
        entity_id: alarm_control_panel.home
    action:
      - choose:
          # Armed Away
          - conditions:
              - condition: state
                entity_id: alarm_control_panel.home
                state: armed_away
            sequence:
              - service: wled_effects.start_effect
                data:
                  effect_name: alert
                  config:
                    severity: info
                    pattern: steady
                    color: "0,255,0"  # Green
          
          # Triggered
          - conditions:
              - condition: state
                entity_id: alarm_control_panel.home
                state: triggered
            sequence:
              - service: wled_effects.start_effect
                data:
                  effect_name: alert
                  config:
                    severity: critical
                    pattern: strobe
                    acknowledge_entity: input_boolean.alarm_ack
```

### Smart Home Notifications

```yaml
automation:
  - alias: "Priority Notifications"
    trigger:
      - platform: state
        entity_id: sensor.notification_count
    action:
      - service: wled_effects.start_effect
        data:
          effect_name: alert
          config:
            severity: auto
            state_entity: sensor.notification_priority
            pattern: auto
            max_duration: 60
            severity_thresholds:
              debug: 1
              info: 2
              warning: 5
              alert: 8
```

### System Monitoring

```yaml
automation:
  - alias: "Server Health Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.server_temperature
        above: 70
    action:
      - service: wled_effects.start_effect
        data:
          effect_name: alert
          config:
            severity: warning
            pattern: double_pulse
            color: "255,100,0"
            escalate_after: 120  # Escalate if temp stays high
            acknowledge_entity: input_boolean.temp_alert_ack
```

### Door/Window Status

```yaml
automation:
  - alias: "Door Left Open"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: 'on'
        for:
          minutes: 5
    action:
      - service: wled_effects.start_effect
        data:
          effect_name: alert
          config:
            severity: warning
            pattern: blink
            flash_rate: 1.0
            color: "255,200,0"
            affected_area: center
            max_duration: 300
```

### Laundry/Timer Completion

```yaml
automation:
  - alias: "Laundry Done"
    trigger:
      - platform: state
        entity_id: sensor.washer_state
        to: 'complete'
    action:
      - service: wled_effects.start_effect
        data:
          effect_name: alert
          config:
            severity: info
            pattern: sparkle_burst
            color: "0,255,150"
            sparkle_count: 50
            max_duration: 60
            acknowledge_entity: input_boolean.laundry_ack
```

---

## Pattern Comparison

### When to Use Each Pattern

| Pattern | Urgency | Attention Level | Best For |
|---------|---------|-----------------|----------|
| **Steady** | Low | Passive | Status indicators, ongoing states |
| **Pulse** | Low-Med | Gentle | Friendly notifications, info |
| **Blink** | Medium | Moderate | Standard alerts, reminders |
| **Double Pulse** | Medium-High | Noticeable | Warnings, caution required |
| **Triple Pulse** | High | Attention-grabbing | Urgent alerts, errors |
| **Strobe** | Critical | Maximum | Emergencies, critical failures |
| **Sparkle Burst** | Variable | Dramatic | Celebrations, important events |

---

## Configuration Parameters Reference

### Core Settings

| Parameter | Type | Default | Range/Options |
|-----------|------|---------|---------------|
| `severity` | string | "info" | debug, info, warning, alert, critical, auto |
| `pattern` | string | "auto" | auto, steady, blink, pulse, double_pulse, triple_pulse, strobe, sparkle_burst |
| `flash_rate` | number | 0.0 | 0.0-10.0 Hz (0 = use default) |
| `duty_cycle` | number | 0.5 | 0.1-0.9 (on-time %) |
| `color` | string | "auto" | "R,G,B" or "auto" |
| `secondary_color` | string | "255,255,255" | "R,G,B" for alternating |

### Sparkle Settings

| Parameter | Type | Default | Range |
|-----------|------|---------|-------|
| `sparkle_count` | integer | 50 | 10-200 |
| `sparkle_decay` | number | 0.85 | 0.5-0.98 |

### Area Settings

| Parameter | Type | Default | Options |
|-----------|------|---------|---------|
| `affected_area` | string | "full" | full, center, edges, random |

### Advanced Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `escalate_after` | number | 0.0 | Seconds before escalating (0 = disabled) |
| `max_duration` | number | 0.0 | Auto-stop seconds (0 = infinite) |
| `acknowledge_entity` | string | - | Entity to check for acknowledgment |
| `state_entity` | string | - | Entity for auto-severity |
| `state_attribute` | string | - | Optional attribute to monitor |
| `severity_thresholds` | object | {...} | State value → severity mapping |

---

## Technical Details

### Severity Escalation Path
```
DEBUG → INFO → WARNING → ALERT → CRITICAL
```

Each escalation doubles the urgency and changes pattern/color.

### Pattern Timing

- **Blink**: On for `duty_cycle` of period
- **Double Pulse**: Two 15% flashes at 0% and 30% of period
- **Triple Pulse**: Three 10% flashes at 0%, 20%, and 40% of period
- **Strobe**: Brief 10% flash (5% white for critical)
- **Sparkle Burst**: 20% spawn window with continuous decay

### Acknowledgment Logic

Entity states that trigger acknowledgment:
- `on`, `true`, `1`, `acknowledged` (case-insensitive)

### Performance

- **Update Rate**: 50ms (20 FPS)
- **CPU Load**: Low-Medium (sparkle_burst slightly higher)
- **Memory**: Minimal + sparkle tracking array
- **Latency**: <100ms state response

---

## Comparison with Other Effects

| Effect | Purpose | Attention | Continuity |
|--------|---------|-----------|------------|
| **Alert** | Notifications | High | Event-based |
| **Breathe** | Ambient/calming | Low-Med | Continuous |
| **Sparkle** | Activity indicator | Low | Continuous |
| **Chase** | Direction/flow | Medium | Continuous |
| **Meter** | Data visualization | Low | Continuous |

---

## Best Practices

### 1. Match Severity to Urgency
- Use **info/warning** for informational alerts
- Use **alert** for time-sensitive issues
- Reserve **critical** for true emergencies

### 2. Consider Context
- **Daytime**: Higher flash rates acceptable
- **Nighttime**: Use gentle patterns (pulse, slow blink)
- **Public spaces**: Consider seizure triggers (avoid very rapid strobes)

### 3. Provide Acknowledgment
- Always include `acknowledge_entity` for persistent alerts
- Use `max_duration` as backup safety

### 4. Test Patterns
- Different patterns work better in different environments
- Sparkle burst is dramatic but may be too much for some contexts

### 5. Use Auto-Severity Wisely
- Set meaningful thresholds
- Consider rate of change, not just absolute values

---

## Integration with System Features

### ✅ Fully Supported

- **StateSourceCoordinator**: For auto-severity and acknowledgment
- **Data Mapping**: Threshold → severity mapping
- **Trigger System**: Can be triggered by events
- **Multi-Zone**: Different alerts in different zones
- **Reverse Direction**: Flip LED order
- **Blend Modes**: Combine with other effects
- **Manual Override**: Freeze on manual control
- **Smoothing**: N/A (discrete patterns)

---

## Troubleshooting

### Alert Not Stopping
- Check `acknowledge_entity` state
- Verify `max_duration` is set
- Check if manual override is active

### Pattern Too Fast/Slow
- Adjust `flash_rate` parameter
- Change to different severity level
- Try different `pattern` type

### Colors Not Right
- Use `color` to override severity defaults
- Check if WLED brightness is set correctly
- Verify RGB values are 0-255

### Escalation Too Aggressive
- Increase `escalate_after` value
- Start with lower initial `severity`
- Use `max_duration` to limit

---

## See Also

- [EFFECTS_QUICK_REFERENCE.md](EFFECTS_QUICK_REFERENCE.md) - All effects comparison
- [NEW_EFFECTS_GUIDE.md](NEW_EFFECTS_GUIDE.md) - Other v2.1 effects
- [CONTEXT_AWARE_FEATURES.md](CONTEXT_AWARE_FEATURES.md) - Base system features
- [README.md](README.md) - Main integration documentation
