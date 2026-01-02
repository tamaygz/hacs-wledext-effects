# State-Reactive Effects Implementation

## Overview

All effects in the WLED Effects integration now support optional state-reactive operation. This means effects can:

1. **React to Home Assistant entity states** - Modulate effect parameters based on sensor values, input numbers, etc.
2. **Fall back gracefully** - Continue working normally if no state entity is configured
3. **Support multiple control modes** - Each effect offers different ways to use state data

## Effect Capabilities

### Rainbow Wave Effect

**State Control Options:**
- `speed` - State controls wave animation speed (1-100)
- `wavelength` - State controls rainbow wave length (10-200 LEDs)
- `both` - State controls both speed and wavelength simultaneously

**Configuration Example:**
```yaml
- name: "Dynamic Rainbow"
  effect_type: "rainbow_wave"
  wave_speed: 10.0
  wave_length: 60
  state_entity: "sensor.room_temperature"
  state_controls: "speed"
  state_min: 15.0
  state_max: 30.0
```

**Behavior:**
- Without state: Animates at configured `wave_speed` and `wave_length`
- With state: Maps entity value to speed or wavelength dynamically

---

### Segment Fade Effect

**State Control Options:**
- `speed` - State controls transition speed (0.1x to 10x multiplier)
- `position` - State directly controls position in fade cycle (0-100% = color1 to color2)

**Configuration Example:**
```yaml
- name: "Mood Fade"
  effect_type: "segment_fade"
  color1: "255,0,0"
  color2: "0,0,255"
  transition_speed: 2.0
  state_entity: "input_number.mood_slider"
  state_controls: "position"
  state_min: 0.0
  state_max: 100.0
```

**Behavior:**
- Without state: Auto-cycles between color1 and color2
- With `speed` mode: Transitions faster/slower based on state
- With `position` mode: Shows exact color at that position (acts like a color picker)

---

### Loading Effect

**State Control Options:**
- `speed` - State controls movement speed (0.01-1.0 seconds per step)
- `position` - State directly controls bar position (0-100% = start to end)
- `bar_size` - State controls bar size (1-50 LEDs)

**Configuration Example:**
```yaml
- name: "CPU Monitor"
  effect_type: "loading"
  color: "0,255,0"
  bar_size: 5
  state_entity: "sensor.cpu_usage"
  state_controls: "position"
  state_min: 0.0
  state_max: 100.0
```

**Behavior:**
- Without state: Auto-bounces across LEDs
- With `speed` mode: Moves faster/slower based on state
- With `position` mode: Bar stays at position representing state value (perfect for progress bars)
- With `bar_size` mode: Bar size changes dynamically

---

### State Sync Effect

**State Control Options:**
- Multiple zones, advanced blending, smoothing, triggers
- See [CONTEXT_AWARE_FEATURES.md](CONTEXT_AWARE_FEATURES.md) for full details

**Configuration Example:**
```yaml
- name: "Audio Visualizer"
  effect_type: "state_sync"
  visualization_mode: "bar_graph"
  state_entity: "sensor.audio_level"
  state_min: 0.0
  state_max: 100.0
  blend_mode: "smooth"
  smoothing_window: 5
```

---

## Common Configuration Parameters

All state-reactive effects share these configuration options:

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `state_entity` | string | Entity ID to monitor | No |
| `state_attribute` | string | Specific attribute to monitor | No |
| `state_controls` | string | What parameter state controls | No |
| `state_min` | number | Minimum expected state value | No (default: 0.0) |
| `state_max` | number | Maximum expected state value | No (default: 100.0) |

## Implementation Details

### StateSourceCoordinator

Each effect that uses state monitoring creates an instance of `StateSourceCoordinator`:

```python
self.state_coordinator = StateSourceCoordinator(
    self.hass,
    self.state_entity,
    self.state_attribute,
)
await self.state_coordinator.async_setup()
```

### State Value Normalization

Effects normalize state values to 0.0-1.0 range:

```python
def _get_state_value(self) -> float:
    """Get normalized state value (0.0 to 1.0)."""
    raw_value = self.state_coordinator.get_numeric_value(
        self.state_min, self.state_max
    )
    
    value_range = self.state_max - self.state_min
    normalized = (raw_value - self.state_min) / value_range
    return max(0.0, min(1.0, normalized))
```

### Parameter Mapping

Effects use the base class `map_value()` method for smooth mapping:

```python
# Map normalized state (0-1) to speed range (1-100)
current_speed = self.map_value(
    state_value, 0.0, 1.0, 1.0, 100.0, smooth=True
)
```

## Usage Examples

### 1. Temperature-Driven Wave Speed

```yaml
- name: "Temperature Wave"
  effect_type: "rainbow_wave"
  state_entity: "sensor.living_room_temperature"
  state_controls: "speed"
  state_min: 18.0  # Cold = slow
  state_max: 28.0  # Hot = fast
```

### 2. Music Volume Bar

```yaml
- name: "Music Visualizer"
  effect_type: "loading"
  color: "0,255,255"
  state_entity: "media_player.spotify"
  state_attribute: "volume_level"
  state_controls: "bar_size"
  state_min: 0.0
  state_max: 1.0
```

### 3. Battery Level Fade

```yaml
- name: "Battery Status"
  effect_type: "segment_fade"
  color1: "255,0,0"    # Red = low
  color2: "0,255,0"    # Green = full
  state_entity: "sensor.phone_battery"
  state_controls: "position"
  state_min: 0.0
  state_max: 100.0
```

### 4. CPU Usage Progress

```yaml
- name: "CPU Monitor"
  effect_type: "loading"
  color: "255,165,0"
  state_entity: "sensor.processor_use"
  state_controls: "position"
  state_min: 0.0
  state_max: 100.0
  trail_fade: true
```

## Compatibility

- All effects remain **fully functional without state configuration**
- State support is **entirely optional**
- Effects gracefully handle:
  - Missing state entities
  - Unavailable states
  - Invalid state values
  - Disconnected coordinators

## See Also

- [CONTEXT_AWARE_FEATURES.md](CONTEXT_AWARE_FEATURES.md) - Advanced context-aware features
- [README.md](README.md) - Main integration documentation
- [legacy_project_for_context/docs/README_EFFECTS.md](legacy_project_for_context/docs/README_EFFECTS.md) - Original effect system
