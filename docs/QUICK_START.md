# Quick Start Guide

Get your first WLED effect running in under 5 minutes!

## Prerequisites Check

Before starting, verify you have:

- ✅ WLED Effects integration installed ([Installation Guide](INSTALLATION.md))
- ✅ WLED device configured in Home Assistant
- ✅ WLED device is online and accessible

## Your First Effect in 5 Steps

### Step 1: Add the Integration (30 seconds)

1. Navigate to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"WLED Effects"**
4. Click on it

### Step 2: Select Your WLED Device (30 seconds)

1. Choose your WLED device from the dropdown
2. If you have multiple devices, pick one to start with
3. Click **Next**

### Step 3: Choose an Effect (1 minute)

Start with **Rainbow Wave** - it's simple and looks great:

1. Select **Effect Type**: `Rainbow Wave`
2. Use the default configuration or customize:
   - **Wave Speed**: `10.0` (how fast the rainbow moves)
   - **Wave Length**: `60` (how stretched the rainbow is)
3. Click **Submit**

### Step 4: Turn It On! (10 seconds)

The integration creates a switch entity. Turn it on:

**Option A - Via UI**:
1. Go to **Settings** → **Devices & Services** → **WLED Effects**
2. Click on your effect
3. Toggle the switch **ON**

**Option B - Via Developer Tools**:
1. Go to **Developer Tools** → **Services**
2. Call this service:

```yaml
service: switch.turn_on
target:
  entity_id: switch.wled_context_effects_rainbow_wave
```

### Step 5: Enjoy! 🎉

Your LED strip should now display a flowing rainbow animation!

---

## What's Next?

### Customize Your Effect

Adjust parameters using the number entities:

```yaml
service: number.set_value
target:
  entity_id: number.wled_context_effects_rainbow_wave_speed
data:
  value: 20  # Twice as fast!
```

Or via the UI:
1. Go to the effect's device page
2. Adjust the sliders for brightness, speed, etc.

### Try Different Effects

Create a new configuration entry for a different effect:

**State Sync** (visualize a sensor):
```yaml
Effect Type: state_sync
Config:
  state_entity: sensor.cpu_usage
  min_value: 0
  max_value: 100
  animation_mode: fill
  color_low: "0,255,0"    # Green
  color_high: "255,0,0"   # Red
```

**Loading Bar** (moving animation):
```yaml
Effect Type: loading
Config:
  color: "0,255,0"
  bar_size: 10
  speed: 0.05
  trail_fade: true
```

---

## Quick Examples

### Example 1: Temperature Visualization

Visualize room temperature with color:

1. Add new WLED Effects integration
2. Select **State Sync** effect
3. Configure:

```yaml
state_entity: sensor.living_room_temperature
min_value: 15
max_value: 30
animation_mode: solid
color_low: "0,0,255"      # Blue for cold
color_high: "255,0,0"     # Red for hot
transition_mode: smooth
```

4. Turn it on!

Result: LEDs change color based on temperature - blue when cold, red when hot.

### Example 2: Loading Animation

Create a moving progress bar:

1. Add new WLED Effects integration
2. Select **Loading** effect
3. Configure:

```yaml
color: "0,255,255"    # Cyan
bar_size: 8
speed: 0.1
trail_fade: true
reverse_direction: false
```

4. Turn it on!

Result: A cyan bar moves across your LED strip with a trailing fade effect.

### Example 3: Notification Alert

Create an attention-grabbing alert:

1. Add new WLED Effects integration
2. Select **Alert** effect
3. Configure:

```yaml
severity: warning
pattern: double_pulse
color: "255,165,0"    # Orange
flash_rate: 2.0
max_duration: 60      # Auto-stop after 1 minute
```

4. Turn it on when needed via automation!

Result: Orange double-pulse pattern that stops automatically.

---

## Using Effects in Automations

Once configured, use effects in your automations:

### Automation Example: Motion-Activated Rainbow

```yaml
automation:
  - alias: "Hallway Motion Rainbow"
    trigger:
      - platform: state
        entity_id: binary_sensor.hallway_motion
        to: 'on'
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.wled_context_effects_rainbow_wave
      - delay:
          minutes: 5
      - service: switch.turn_off
        target:
          entity_id: switch.wled_context_effects_rainbow_wave
```

### Automation Example: CPU Alert

```yaml
automation:
  - alias: "High CPU Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.processor_use
        above: 90
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.wled_context_effects_alert_critical
```

---

## Entity Types Explained

Each effect creates these entities:

### Switch Entity
**Purpose**: Turn effect on/off  
**Example**: `switch.wled_context_effects_rainbow_wave`

```yaml
# Turn on
service: switch.turn_on
target:
  entity_id: switch.wled_context_effects_rainbow_wave

# Turn off
service: switch.turn_off
target:
  entity_id: switch.wled_context_effects_rainbow_wave
```

### Number Entities
**Purpose**: Adjust effect parameters  
**Examples**:
- `number.wled_context_effects_rainbow_wave_brightness` (0-255)
- `number.wled_context_effects_rainbow_wave_speed` (varies by effect)

```yaml
service: number.set_value
target:
  entity_id: number.wled_context_effects_rainbow_wave_brightness
data:
  value: 200
```

### Select Entity
**Purpose**: Choose effect modes  
**Example**: `select.wled_context_effects_state_sync_animation_mode`

```yaml
service: select.select_option
target:
  entity_id: select.wled_context_effects_state_sync_animation_mode
data:
  option: "fill"
```

### Sensor Entities
**Purpose**: Monitor effect status  
**Examples**:
- `sensor.wled_context_effects_rainbow_wave_status` - Current state
- `sensor.wled_context_effects_rainbow_wave_frame_rate` - Performance

### Button Entity
**Purpose**: Trigger actions  
**Example**: `button.wled_context_effects_rainbow_wave_restart`

```yaml
service: button.press
target:
  entity_id: button.wled_context_effects_rainbow_wave_restart
```

---

## Services Overview

### Start Effect

```yaml
service: switch.turn_on
target:
  entity_id: switch.wled_context_effects_<effect_name>
```

### Stop Effect

```yaml
service: switch.turn_off
target:
  entity_id: switch.wled_context_effects_<effect_name>
```

### Update Configuration

```yaml
service: number.set_value
target:
  entity_id: number.wled_context_effects_<effect_name>_<parameter>
data:
  value: <new_value>
```

---

## Common Patterns

### Pattern 1: Temporary Effect

Turn on an effect for a specific duration:

```yaml
- service: switch.turn_on
  target:
    entity_id: switch.wled_context_effects_alert
- delay: "00:02:00"  # 2 minutes
- service: switch.turn_off
  target:
    entity_id: switch.wled_context_effects_alert
```

### Pattern 2: Conditional Effects

Different effects based on conditions:

```yaml
- choose:
    - conditions:
        - condition: numeric_state
          entity_id: sensor.cpu_usage
          above: 80
      sequence:
        - service: switch.turn_on
          target:
            entity_id: switch.wled_context_effects_alert_high_cpu
    - conditions:
        - condition: numeric_state
          entity_id: sensor.cpu_usage
          below: 30
      sequence:
        - service: switch.turn_on
          target:
            entity_id: switch.wled_context_effects_rainbow_calm
```

### Pattern 3: Time-Based Effects

Different effects for different times of day:

```yaml
- service: switch.turn_on
  target:
    entity_id: >
      {% if now().hour < 8 %}
        switch.wled_context_effects_breathe_calm
      {% elif now().hour < 20 %}
        switch.wled_context_effects_rainbow_bright
      {% else %}
        switch.wled_context_effects_breathe_dim
      {% endif %}
```

---

## Tips for Beginners

### 1. Start Simple
Begin with standalone effects (Rainbow Wave, Loading) before trying state-driven effects.

### 2. Test Each Effect
Create one effect at a time and test it before adding more.

### 3. Use Default Values
Default configurations are designed to work well - customize gradually.

### 4. Check Logs
If something doesn't work, check: **Settings** → **System** → **Logs**

### 5. One Device at a Time
If you have multiple WLED devices, configure one completely before adding others.

---

## Next Steps

Ready to dive deeper?

- **[Effects Reference](EFFECTS_REFERENCE.md)** - Detailed guide to all 9 effects
- **[Context-Aware Features](CONTEXT_AWARE_FEATURES.md)** - Make effects react to your smart home
- **[Advanced Guide](ADVANCED_GUIDE.md)** - Triggers, data mapping, and complex automations
- **[Services API](SERVICES_API.md)** - Complete service documentation

---

## Need Help?

Having trouble? Check:

- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
- **[GitHub Discussions](https://github.com/tamaygz/hacs-wledext-effects/discussions)** - Community support

---

**Happy LED controlling!** 🌈✨

---

**Last Updated**: January 2026  
**Version**: 1.0.0
