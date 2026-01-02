# WLED Effects Integration - Technical Specification

## Executive Summary

This document specifies a modern Home Assistant HACS integration for managing custom WLED effects. The integration provides a UI-driven, entity-based approach to creating, configuring, and controlling advanced lighting effects on WLED devices, replacing the current pyscript-based implementation.

## Goals

1. **Native Integration**: Full Home Assistant integration following official architecture patterns
2. **User-Friendly**: Configuration through UI, not YAML
3. **Extensible**: Easy addition of new effects with modular architecture
4. **Reliable**: Robust error handling, state recovery, and connection management
5. **Observable**: Rich entity representation for dashboards and automations
6. **Performant**: Efficient communication with WLED devices using official library

## Architecture Overview

### Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│  Home Assistant UI (Config Flow, Entities, Cards)   │
└─────────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────────┐
│         Integration Layer (Platforms & Services)     │
├─────────────────────────────────────────────────────┤
│  • Config Flow          • Switch Platform           │
│  • Coordinators         • Select Platform           │
│  • Services             • Number Platform           │
│  • Events               • Sensor Platform           │
│                         • Button Platform           │
└─────────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────────┐
│           Effect Framework Layer                     │
├─────────────────────────────────────────────────────┤
│  • EffectBase (Abstract)                            │
│  • WLEDEffectBase (Concrete)                        │
│  • Effect Discovery & Loading                       │
│  • Common Utilities                                 │
└─────────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────────┐
│          Effect Implementations                      │
├─────────────────────────────────────────────────────┤
│  • Rainbow Wave      • Loading                      │
│  • Segment Fade      • State Sync                   │
│  • [User-defined effects]                           │
└─────────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────────┐
│          Communication Layer                         │
├─────────────────────────────────────────────────────┤
│  • python-wled Library (Official WLED Client)       │
│  • Connection Management                            │
│  • Retry Logic & Error Handling                     │
└─────────────────────────────────────────────────────┘
```

## Core Components

### 1. Configuration Flow

**Purpose**: UI-based setup of effect configurations

**Flow Steps**:

1. **Device Selection**
   - List all available WLED devices from existing integrations
   - Allow manual IP entry if device not found
   - Validate connectivity

2. **Effect Type Selection**
   - Present dropdown of available effect types
   - Show description and preview for each effect
   - Display requirements (e.g., "Requires state source")

3. **Effect Configuration**
   - Dynamic form based on effect schema
   - Common parameters:
     - Effect name (user-friendly identifier)
     - Segment ID (with auto-detect option)
     - LED range (start/stop indices)
     - Brightness
   - Effect-specific parameters:
     - Animation mode (for applicable effects)
     - Colors (color pickers)
     - Speeds/transitions
     - State source entity (for reactive effects)

4. **Confirmation**
   - Review configuration
   - Test effect (preview mode)
   - Create config entry

**Options Flow**:
- Modify existing effect configuration
- Enable/disable effect
- Delete effect

### 2. Coordinators

#### EffectCoordinator

**Responsibility**: Manage effect lifecycle and state

```python
class EffectCoordinator(DataUpdateCoordinator):
    """Coordinate effect state and execution."""
    
    - Manages effect start/stop
    - Tracks running state
    - Handles errors and recovery
    - Provides state to entities
    - Coordinates with WLED device
```

**Update Interval**: On-demand (event-driven) + periodic health check (30s)

**Data Structure**:
```python
{
    "running": bool,
    "effect_type": str,
    "last_update": datetime,
    "error": str | None,
    "statistics": {
        "commands_sent": int,
        "commands_succeeded": int,
        "last_error": str | None
    }
}
```

#### StateSourceCoordinator

**Responsibility**: Track state changes for reactive effects

```python
class StateSourceCoordinator(DataUpdateCoordinator):
    """Track state changes from Home Assistant entities."""
    
    - Monitors target entity state/attribute
    - Provides current value to effects
    - Notifies on changes
    - Handles unavailable states
```

**Update Interval**: Configurable (default 0.5s for responsive effects)

### 3. Entity Platforms

#### Switch Platform

**Entity per Effect**: On/Off control

```python
WLEDEffectSwitch(SwitchEntity):
    - Turn on: Start effect
    - Turn off: Stop effect
    - State: Running status
    - Icon: Dynamic based on effect type
```

**Attributes**:
- `effect_type`: Name of effect
- `segment_id`: Target segment
- `last_started`: Timestamp
- `command_count`: Total commands sent

#### Select Platform

**Effect Type Selector** (optional, for dynamic switching):
```python
WLEDEffectTypeSelect(SelectEntity):
    - Options: List of available effect types
    - Change: Reconfigure effect with new type
```

**Animation Mode Selector** (effect-specific):
```python
WLEDEffectModeSelect(SelectEntity):
    - Options: Effect-specific modes
    - Example: ["Single", "Dual", "Center"] for State Sync
```

#### Number Platform

**Configurable Parameters**:

```python
# Brightness
WLEDEffectBrightnessNumber(NumberEntity):
    - Range: 0-255
    - Mode: Slider
    
# Speed/Transition Speed
WLEDEffectSpeedNumber(NumberEntity):
    - Range: Effect-specific
    - Mode: Slider
    
# Segment ID
WLEDEffectSegmentNumber(NumberEntity):
    - Range: 0-31
    - Mode: Box
    
# LED Range
WLEDEffectStartLEDNumber(NumberEntity):
WLEDEffectStopLEDNumber(NumberEntity):
    - Range: 0-device max
    - Mode: Box
```

#### Sensor Platform

**Status Sensors**:

```python
WLEDEffectStatusSensor(SensorEntity):
    - State: "running" | "stopped" | "error"
    - Device class: enum
    
WLEDEffectSuccessRateSensor(SensorEntity):
    - State: Percentage of successful commands
    - Unit: %
    
WLEDEffectLastErrorSensor(SensorEntity):
    - State: Last error message or "None"
```

#### Button Platform

```python
WLEDEffectRunOnceButton(ButtonEntity):
    - Press: Execute effect once (non-continuous)
    - Use case: One-shot animations
```

### 4. Services

#### Core Services

```yaml
wled_effects.start_effect:
  description: Start a configured effect
  fields:
    entity_id:
      description: Effect switch entity ID
      required: true
      selector:
        entity:
          integration: wled_effects
          domain: switch

wled_effects.stop_effect:
  description: Stop a running effect
  fields:
    entity_id:
      description: Effect switch entity ID
      required: true
      selector:
        entity:
          integration: wled_effects
          domain: switch

wled_effects.run_once:
  description: Run effect once (single iteration)
  fields:
    entity_id:
      description: Effect switch entity ID
      required: true
      selector:
        entity:
          integration: wled_effects
          domain: switch

wled_effects.set_config:
  description: Update effect configuration dynamically
  fields:
    entity_id:
      description: Effect switch entity ID
      required: true
      selector:
        entity:
          integration: wled_effects
          domain: switch
    config:
      description: Configuration dictionary
      required: true
      example: {"anim_mode": "Dual", "sync_color": [255, 0, 0]}
      selector:
        object:

wled_effects.reload:
  description: Reload effect modules (development)
  fields: {}
```

### 5. Events

**Event Types**:

```python
# Effect started
wled_effects_started:
  event_data:
    entity_id: str
    effect_type: str
    segment_id: int

# Effect stopped  
wled_effects_stopped:
  event_data:
    entity_id: str
    effect_type: str
    duration: float  # seconds running

# Effect error
wled_effects_error:
  event_data:
    entity_id: str
    effect_type: str
    error: str
    recoverable: bool

# Configuration changed
wled_effects_config_changed:
  event_data:
    entity_id: str
    old_config: dict
    new_config: dict
```

**Usage Example**:
```yaml
automation:
  - trigger:
      - platform: event
        event_type: wled_effects_error
        event_data:
          entity_id: switch.rainbow_wave_effect
    action:
      - service: notify.mobile_app
        data:
          message: "WLED effect error: {{ trigger.event.data.error }}"
```

## Effect Framework

### Base Classes

#### Abstract Effect Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class EffectProtocol(Protocol):
    """Protocol defining the effect interface."""
    
    async def start(self) -> None:
        """Start the effect (continuous mode)."""
        ...
    
    async def stop(self) -> None:
        """Stop the effect."""
        ...
    
    async def run_once(self) -> None:
        """Execute effect once."""
        ...
    
    @property
    def running(self) -> bool:
        """Return if effect is currently running."""
        ...
    
    @property
    def config_schema(self) -> dict:
        """Return JSON schema for effect configuration."""
        ...
    
    def get_effect_name(self) -> str:
        """Return human-readable effect name."""
        ...
```

#### Concrete Base Implementation

```python
from wled import WLED
from homeassistant.core import HomeAssistant

class WLEDEffectBase:
    """Base class for WLED effects using python-wled library."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        wled_client: WLED,
        config: dict
    ):
        """Initialize effect.
        
        Args:
            hass: Home Assistant instance
            wled_client: python-wled WLED client instance
            config: Effect configuration dictionary
        """
        self.hass = hass
        self.wled = wled_client
        self.config = config
        self._running = False
        self._task = None
        
        # Extract common config
        self.segment_id = config.get("segment_id", 0)
        self.start_led = config.get("start_led")
        self.stop_led = config.get("stop_led")
        self.brightness = config.get("brightness", 255)
        
    async def setup(self) -> bool:
        """Setup effect (called once after init).
        
        Returns:
            True if setup successful
        """
        # Auto-detect LED range if not specified
        if self.start_led is None or self.stop_led is None:
            await self._auto_detect_range()
        
        return True
    
    async def start(self) -> None:
        """Start effect in continuous mode."""
        if self._running:
            return
        
        self._running = True
        self._task = self.hass.async_create_task(
            self._run_loop()
        )
    
    async def stop(self) -> None:
        """Stop the effect."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    async def run_once(self) -> None:
        """Run effect once."""
        await self.run_effect()
    
    async def _run_loop(self) -> None:
        """Main effect loop (continuous mode)."""
        while self._running:
            try:
                await self.run_effect()
                await asyncio.sleep(0.01)  # Prevent tight loop
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Effect error: %s", err)
                await asyncio.sleep(1)  # Back off on error
    
    async def run_effect(self) -> None:
        """Effect implementation - override in subclass."""
        raise NotImplementedError
    
    async def send_wled_command(self, **kwargs) -> bool:
        """Send command to WLED device.
        
        Args:
            **kwargs: Arguments passed to wled.segment()
        
        Returns:
            True if command successful
        """
        try:
            await self.wled.segment(
                segment_id=self.segment_id,
                **kwargs
            )
            return True
        except Exception as err:
            _LOGGER.error("WLED command failed: %s", err)
            return False
    
    async def _auto_detect_range(self) -> None:
        """Auto-detect LED range from device."""
        device = await self.wled.update()
        if device.info.leds.count:
            self.start_led = 0
            self.stop_led = device.info.leds.count - 1
    
    @property
    def running(self) -> bool:
        """Return running state."""
        return self._running
    
    @classmethod
    def config_schema(cls) -> dict:
        """Return config schema for effect.
        
        Override to add effect-specific fields.
        """
        return {
            "type": "object",
            "properties": {
                "segment_id": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 31,
                    "default": 0
                },
                "start_led": {
                    "type": "integer",
                    "minimum": 0
                },
                "stop_led": {
                    "type": "integer",
                    "minimum": 0
                },
                "brightness": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "default": 255
                }
            }
        }
    
    def get_effect_name(self) -> str:
        """Return effect name."""
        return self.__class__.__name__
```

### Effect Discovery & Registration

```python
class EffectRegistry:
    """Registry for available effects."""
    
    def __init__(self):
        self._effects = {}
    
    def register(self, effect_class: Type[WLEDEffectBase]) -> None:
        """Register an effect class."""
        name = effect_class.__name__
        self._effects[name] = effect_class
    
    def get_effect_class(self, name: str) -> Type[WLEDEffectBase]:
        """Get effect class by name."""
        return self._effects.get(name)
    
    def list_effects(self) -> list[str]:
        """List all registered effects."""
        return list(self._effects.keys())

# Global registry
EFFECT_REGISTRY = EffectRegistry()

# Decorator for registration
def register_effect(cls):
    """Decorator to register effect class."""
    EFFECT_REGISTRY.register(cls)
    return cls
```

### Example Effect Implementation

```python
@register_effect
class RainbowWaveEffect(WLEDEffectBase):
    """Rainbow wave effect."""
    
    def __init__(self, hass: HomeAssistant, wled_client: WLED, config: dict):
        super().__init__(hass, wled_client, config)
        self.wave_speed = config.get("wave_speed", 1.0)
        self.color_shift = 0
    
    async def run_effect(self) -> None:
        """Render rainbow wave."""
        # Generate rainbow colors
        colors = []
        for i in range(self.start_led, self.stop_led + 1):
            hue = (i * 10 + self.color_shift) % 360
            colors.append(self._hue_to_rgb(hue))
        
        # Send to WLED
        await self.send_wled_command(
            color_primary=colors,
            brightness=self.brightness
        )
        
        # Advance wave
        self.color_shift = (self.color_shift + self.wave_speed) % 360
    
    @classmethod
    def config_schema(cls) -> dict:
        """Extend base schema with effect-specific fields."""
        schema = super().config_schema()
        schema["properties"]["wave_speed"] = {
            "type": "number",
            "minimum": 0.1,
            "maximum": 10.0,
            "default": 1.0,
            "description": "Speed of the wave animation"
        }
        return schema
    
    @staticmethod
    def _hue_to_rgb(hue: int) -> tuple[int, int, int]:
        """Convert HSV to RGB (full saturation, full value)."""
        # Implementation omitted for brevity
        ...
```

## Device Integration

### Device Registry

Each effect configuration creates a device entry:

```python
device_info = DeviceInfo(
    identifiers={(DOMAIN, f"{wled_device_id}_{effect_id}")},
    name=f"{effect_name} Effect",
    manufacturer="WLED Effects",
    model=effect_type,
    via_device=(WLED_DOMAIN, wled_device_id),  # Link to WLED device
    configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}"
)
```

**Benefits**:
- Effects appear as devices in UI
- Clear hierarchy (WLED device → Effect devices)
- Easy management and organization
- Diagnostic information per effect

## Communication Layer

### Using python-wled Library

The integration uses the official `python-wled` library (already included in Home Assistant core):

**Key Features**:
- Async/await native
- Type hints throughout
- Automatic retry logic
- Connection pooling
- WebSocket support (for real-time updates)
- JSON API abstraction

**Advantages over direct HTTP**:
- Less code to maintain
- Battle-tested error handling
- Automatic discovery support
- Consistent with HA's WLED integration
- Future-proof (library maintained)

**Example Usage**:
```python
from wled import WLED

async with WLED("192.168.1.100") as wled:
    # Get device info
    device = await wled.update()
    
    # Set segment
    await wled.segment(
        segment_id=0,
        color_primary=(255, 0, 0),
        brightness=128
    )
    
    # Individual LED control
    await wled.segment(
        segment_id=0,
        leds={
            0: (255, 0, 0),
            1: (0, 255, 0),
            2: (0, 0, 255)
        }
    )
```

### Connection Management

```python
class WLEDConnectionManager:
    """Manage WLED device connections."""
    
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._clients: dict[str, WLED] = {}
    
    async def get_client(self, host: str) -> WLED:
        """Get or create WLED client for host."""
        if host not in self._clients:
            self._clients[host] = WLED(host)
        return self._clients[host]
    
    async def close_all(self) -> None:
        """Close all connections."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
```

## Configuration Storage

### Config Entry Structure

```python
{
    "entry_id": "unique_id_here",
    "version": 1,
    "domain": "wled_effects",
    "title": "Rainbow Wave on Living Room WLED",
    "data": {
        "wled_device_id": "aabbccddeeff",  # Link to WLED integration
        "wled_host": "192.168.1.100",
        "effect_type": "RainbowWaveEffect"
    },
    "options": {
        "effect_name": "Living Room Rainbow",
        "segment_id": 0,
        "start_led": 0,
        "stop_led": 59,
        "brightness": 200,
        "effect_config": {
            "wave_speed": 2.5
        },
        "state_source": {
            "entity_id": "sensor.brightness",  # For reactive effects
            "attribute": null
        },
        "auto_start": false,  # Start on HA startup
        "enabled": true
    }
}
```

### Options Flow

Users can modify configuration via Options:
- All effect parameters
- Enable/disable effect
- Auto-start behavior
- State source (for reactive effects)

## Error Handling & Recovery

### Error Categories

1. **Connection Errors**
   - WLED device unreachable
   - Network timeout
   - **Recovery**: Exponential backoff retry

2. **Configuration Errors**
   - Invalid LED range
   - Invalid segment ID
   - **Recovery**: Validation + user notification

3. **Effect Execution Errors**
   - Runtime exceptions in effect code
   - **Recovery**: Log error, continue running

4. **State Source Errors**
   - Unavailable entity
   - Invalid value
   - **Recovery**: Use fallback value, notify user

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Prevent repeated failures from overwhelming system."""
    
    FAILURE_THRESHOLD = 5
    TIMEOUT = 60  # seconds
    
    def __init__(self):
        self.failures = 0
        self.last_failure = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure > self.TIMEOUT:
                self.state = "half-open"
            else:
                raise CircuitBreakerError("Circuit breaker is open")
        
        try:
            result = await func()
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception as err:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.FAILURE_THRESHOLD:
                self.state = "open"
            raise
```

## Testing Strategy

### Unit Tests

```python
# Test effect base functionality
async def test_effect_start_stop():
    effect = MockEffect(hass, wled_client, config)
    await effect.start()
    assert effect.running
    await effect.stop()
    assert not effect.running

# Test configuration validation
def test_config_schema_validation():
    schema = RainbowWaveEffect.config_schema()
    valid_config = {"wave_speed": 2.5, "segment_id": 0}
    assert validate_schema(schema, valid_config)
    
    invalid_config = {"wave_speed": -1}
    with pytest.raises(ValidationError):
        validate_schema(schema, invalid_config)
```

### Integration Tests

```python
# Test coordinator
async def test_effect_coordinator_update():
    coordinator = EffectCoordinator(hass, effect)
    await coordinator.async_refresh()
    assert coordinator.data["running"] == effect.running

# Test entity creation
async def test_switch_entity_creation():
    entry = MockConfigEntry(domain=DOMAIN, data={...})
    await hass.config_entries.async_setup(entry.entry_id)
    
    state = hass.states.get("switch.test_effect")
    assert state is not None
    assert state.state == "off"
```

### Mock WLED Device

```python
class MockWLED:
    """Mock WLED device for testing."""
    
    def __init__(self):
        self.segments = {}
        self.info = MockInfo()
    
    async def segment(self, segment_id, **kwargs):
        """Mock segment update."""
        self.segments[segment_id] = kwargs
    
    async def update(self):
        """Mock device update."""
        return self
```

## Performance Considerations

### Rate Limiting

```python
class RateLimiter:
    """Limit WLED command rate."""
    
    MAX_COMMANDS_PER_SECOND = 20
    
    def __init__(self):
        self._timestamps = deque(maxlen=self.MAX_COMMANDS_PER_SECOND)
    
    async def acquire(self):
        """Acquire permission to send command."""
        now = time.time()
        
        # Remove old timestamps
        while self._timestamps and now - self._timestamps[0] > 1.0:
            self._timestamps.popleft()
        
        # Check if at limit
        if len(self._timestamps) >= self.MAX_COMMANDS_PER_SECOND:
            sleep_time = 1.0 - (now - self._timestamps[0])
            await asyncio.sleep(sleep_time)
        
        self._timestamps.append(time.time())
```

### Batch Updates

For effects that update multiple parameters:
```python
# Instead of multiple calls:
await wled.segment(segment_id=0, brightness=128)
await wled.segment(segment_id=0, color_primary=(255, 0, 0))

# Batch into one:
await wled.segment(
    segment_id=0,
    brightness=128,
    color_primary=(255, 0, 0)
)
```

## Migration from Pyscript Version

### Migration Tool

```python
class PyscriptMigration:
    """Migrate from pyscript version to integration."""
    
    async def discover_pyscript_effects(self) -> list[dict]:
        """Find existing pyscript effect configurations."""
        # Scan pyscript files
        # Parse service call patterns
        # Extract configurations
        ...
    
    async def create_config_entries(self, configs: list[dict]):
        """Create integration config entries from pyscript configs."""
        for config in configs:
            entry_data = self._convert_config(config)
            await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=entry_data
            )
    
    def _convert_config(self, pyscript_config: dict) -> dict:
        """Convert pyscript config to integration format."""
        # Map service call parameters to config entry structure
        ...
```

### Side-by-Side Operation

During migration:
1. Keep pyscript version installed
2. Install integration version
3. Create integration effects for testing
4. Compare behavior
5. Remove pyscript version when satisfied

### Migration Guide

Documentation includes:
- Step-by-step migration process
- Configuration mapping table
- Troubleshooting common issues
- Rollback procedure

## Documentation

### User Documentation

1. **Installation Guide**
   - HACS installation
   - Requirements
   - First-time setup

2. **Configuration Guide**
   - Adding effects through UI
   - Understanding effect parameters
   - State source configuration

3. **Usage Guide**
   - Controlling effects
   - Dashboard integration
   - Automation examples

4. **Troubleshooting**
   - Common issues
   - Diagnostic tools
   - Support resources

### Developer Documentation

1. **Effect Development Guide**
   - Creating custom effects
   - Effect base class API
   - Configuration schema
   - Testing effects

2. **Architecture Overview**
   - Component diagram
   - Data flow
   - Extension points

3. **API Reference**
   - Base classes
   - Services
   - Events
   - Entities

4. **Contributing Guide**
   - Code style
   - Testing requirements
   - Pull request process

## Future Enhancements

### Phase 2 Features

1. **Effect Chains**
   - Sequential effect execution
   - Conditional transitions
   - Loop control

2. **Effect Groups**
   - Multi-segment synchronization
   - Group-level controls
   - Coordinated animations

3. **Scene Integration**
   - Save effect configurations as scenes
   - Quick preset switching
   - Scene-based scheduling

### Phase 3 Features

1. **Effect Library**
   - Community effect repository
   - One-click installation
   - Rating and reviews
   - Version management

2. **Visual Effect Editor**
   - Drag-and-drop timeline
   - Real-time preview
   - Keyframe animation

3. **AI-Powered Effects**
   - Music reactive (beat detection)
   - Video sync (color extraction)
   - Mood-based selection

## Dependencies

### Required

- Home Assistant Core 2024.1+
- WLED device with firmware 0.14.0+
- `python-wled` library (included in HA core)

### Optional

- Pyscript (for migration only)

## Security Considerations

1. **Input Validation**
   - All user input validated against schemas
   - LED ranges checked against device capabilities
   - Color values sanitized

2. **Rate Limiting**
   - Command rate limiting per device
   - Prevent DoS on WLED devices

3. **Network Security**
   - Support for HTTPS when WLED supports it
   - No credential storage (WLED is local)

4. **Code Safety**
   - No arbitrary code execution
   - Effects run in controlled environment
   - Resource limits (CPU, memory)

## Success Metrics

1. **Functionality**
   - All existing effects ported and working
   - No regressions from pyscript version
   - 95%+ command success rate

2. **Performance**
   - Effect latency < 100ms
   - Smooth animations (30+ FPS for LED updates)
   - HA startup time impact < 1s

3. **Reliability**
   - Automatic recovery from network issues
   - No memory leaks
   - Stable over 30+ day uptimes

4. **Usability**
   - Config flow completion < 2 minutes
   - Clear error messages
   - Positive community feedback

## Conclusion

This specification provides a comprehensive blueprint for a modern, maintainable, and extensible WLED effects integration for Home Assistant. By following Home Assistant's architectural patterns and best practices, leveraging the official `python-wled` library, and providing rich UI integration, this implementation will offer a superior user experience compared to the current pyscript-based approach.

The modular architecture ensures easy addition of new effects, while the robust error handling and state management provide reliability. The entity-based approach integrates seamlessly with Home Assistant's ecosystem, enabling powerful automations and dashboard customizations.

## Appendix A: File Structure

```
custom_components/wled_effects/
├── __init__.py              # Integration setup
├── manifest.json            # Integration metadata
├── config_flow.py          # Configuration UI
├── const.py                # Constants
├── coordinator.py          # Coordinators
├── device.py               # Device info helpers
├── errors.py               # Custom exceptions
├── services.yaml           # Service definitions
├── strings.json            # Translations
├── translations/           # Localization
│   └── en.json
├── platforms/              # Entity platforms
│   ├── __init__.py
│   ├── switch.py          # Switch entities
│   ├── select.py          # Select entities
│   ├── number.py          # Number entities
│   ├── sensor.py          # Sensor entities
│   └── button.py          # Button entities
├── effects/                # Effect implementations
│   ├── __init__.py
│   ├── base.py            # Base classes
│   ├── registry.py        # Effect registry
│   ├── rainbow_wave.py    # Rainbow wave effect
│   ├── segment_fade.py    # Segment fade effect
│   ├── loading.py         # Loading effect
│   └── state_sync.py      # State sync effect
└── tests/                  # Test suite
    ├── __init__.py
    ├── conftest.py        # Test fixtures
    ├── test_config_flow.py
    ├── test_coordinator.py
    ├── test_effects.py
    └── test_entities.py
```

## Appendix B: Example Automation

```yaml
# Start rainbow effect when motion detected
automation:
  - id: motion_rainbow
    alias: "Start Rainbow on Motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion
        to: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.rainbow_wave_effect

# Sync LED brightness to media player volume
automation:
  - id: sync_volume_brightness
    alias: "Sync Volume to LEDs"
    trigger:
      - platform: state
        entity_id: media_player.spotify
        attribute: volume_level
    action:
      - service: number.set_value
        target:
          entity_id: number.volume_sync_brightness
        data:
          value: "{{ (trigger.to_state.attributes.volume_level * 255) | int }}"

# Effect sequence on sunset
automation:
  - id: sunset_sequence
    alias: "Sunset LED Sequence"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.loading_effect
      - delay: "00:00:30"
      - service: switch.turn_off
        target:
          entity_id: switch.loading_effect
      - service: switch.turn_on
        target:
          entity_id: switch.rainbow_wave_effect
```

## Appendix C: Config Flow Screenshots (Mockup)

```
┌────────────────────────────────────────┐
│  Add WLED Effect                       │
├────────────────────────────────────────┤
│                                        │
│  Select WLED Device:                   │
│  [Living Room WLED ▼]                  │
│                                        │
│  [Next]                 [Cancel]       │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Add WLED Effect                       │
├────────────────────────────────────────┤
│                                        │
│  Select Effect Type:                   │
│  [Rainbow Wave ▼]                      │
│                                        │
│  Description:                          │
│  Animated rainbow wave across the LED  │
│  strip with configurable speed.        │
│                                        │
│  [Next]      [Back]      [Cancel]      │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Configure Rainbow Wave                │
├────────────────────────────────────────┤
│                                        │
│  Effect Name:                          │
│  [Living Room Rainbow______]           │
│                                        │
│  Segment ID:                           │
│  [0____] ☑ Auto-detect                 │
│                                        │
│  Brightness:                           │
│  [████████░░] 200                      │
│                                        │
│  Wave Speed:                           │
│  [█████░░░░░] 2.5                      │
│                                        │
│  ☑ Start effect on Home Assistant boot │
│                                        │
│  [Test Effect]                         │
│                                        │
│  [Submit]    [Back]      [Cancel]      │
└────────────────────────────────────────┘
```
