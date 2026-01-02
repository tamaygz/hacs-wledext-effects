# Services API

Complete reference for all WLED Effects services.

## Service List

- [`switch.turn_on`](#switchturn_on) - Start an effect
- [`switch.turn_off`](#switchturn_off) - Stop an effect
- [`number.set_value`](#numberset_value) - Set effect parameter
- [`select.select_option`](#selectselect_option) - Change effect mode
- [`button.press`](#buttonpress) - Trigger action

---

## switch.turn_on

Start an effect.

### Parameters

```yaml
service: switch.turn_on
target:
  entity_id: switch.wled_effects_<effect_name>
```

### Example

```yaml
service: switch.turn_on
target:
  entity_id: switch.wled_effects_rainbow_wave
```

---

## switch.turn_off

Stop a running effect.

### Parameters

```yaml
service: switch.turn_off
target:
  entity_id: switch.wled_effects_<effect_name>
```

### Example

```yaml
service: switch.turn_off
target:
  entity_id: switch.wled_effects_rainbow_wave
```

---

## number.set_value

Update a numeric effect parameter.

### Parameters

```yaml
service: number.set_value
target:
  entity_id: number.wled_effects_<effect_name>_<parameter>
data:
  value: <number>
```

### Examples

**Set brightness**:
```yaml
service: number.set_value
target:
  entity_id: number.wled_effects_rainbow_wave_brightness
data:
  value: 200
```

**Set speed**:
```yaml
service: number.set_value
target:
  entity_id: number.wled_effects_loading_speed
data:
  value: 0.1
```

---

## select.select_option

Change an effect mode or option.

### Parameters

```yaml
service: select.select_option
target:
  entity_id: select.wled_effects_<effect_name>_<parameter>
data:
  option: "<option_value>"
```

### Example

```yaml
service: select.select_option
target:
  entity_id: select.wled_effects_state_sync_animation_mode
data:
  option: "center"
```

---

## button.press

Trigger an action (e.g., restart effect).

### Parameters

```yaml
service: button.press
target:
  entity_id: button.wled_effects_<effect_name>_<action>
```

### Example

```yaml
service: button.press
target:
  entity_id: button.wled_effects_rainbow_wave_restart
```

---

## Automation Examples

### Example 1: Motion-Activated Effect

```yaml
automation:
  - alias: "Motion LED"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion
        to: 'on'
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_loading
      - wait_for_trigger:
          - platform: state
            entity_id: binary_sensor.motion
            to: 'off'
            for: "00:01:00"
      - service: switch.turn_off
        target:
          entity_id: switch.wled_effects_loading
```

### Example 2: Time-Based Speed Adjustment

```yaml
automation:
  - alias: "Slow Down at Night"
    trigger:
      - platform: time
        at: "22:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.wled_effects_rainbow_wave_speed
        data:
          value: 5  # Slower
```

### Example 3: Temperature-Reactive

```yaml
automation:
  - alias: "Temperature Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.temperature
        above: 25
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.wled_effects_alert_warning
```

---

**Last Updated**: January 2026
