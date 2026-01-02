"""Constants for the WLED Effects integration."""
from datetime import timedelta
from typing import Final

# Integration domain
DOMAIN: Final = "wled_context_effects"

# Platforms
PLATFORMS: Final = ["switch", "number", "select", "sensor", "button"]

# Configuration and options
CONF_WLED_DEVICE_ID: Final = "wled_device_id"
CONF_WLED_UNIQUE_ID: Final = "wled_unique_id"
CONF_WLED_HOST: Final = "wled_host"
CONF_EFFECT_TYPE: Final = "effect_type"
CONF_EFFECT_NAME: Final = "effect_name"
CONF_SEGMENT_ID: Final = "segment_id"
CONF_START_LED: Final = "start_led"
CONF_STOP_LED: Final = "stop_led"
CONF_BRIGHTNESS: Final = "brightness"
CONF_EFFECT_CONFIG: Final = "effect_config"
CONF_STATE_SOURCE: Final = "state_source"
CONF_STATE_SOURCE_ENTITY: Final = "entity_id"
CONF_STATE_SOURCE_ATTRIBUTE: Final = "attribute"
CONF_AUTO_START: Final = "auto_start"
CONF_ENABLED: Final = "enabled"
CONF_AUTO_DETECT: Final = "auto_detect"

# Default values
DEFAULT_SEGMENT_ID: Final = 0
DEFAULT_BRIGHTNESS: Final = 255
DEFAULT_AUTO_START: Final = False
DEFAULT_ENABLED: Final = True
DEFAULT_UPDATE_INTERVAL: Final = timedelta(seconds=30)
DEFAULT_STATE_SOURCE_UPDATE_INTERVAL: Final = timedelta(seconds=0.5)
DEFAULT_RETRY_DELAY: Final = 5  # seconds
DEFAULT_MAX_RETRIES: Final = 3
DEFAULT_COMMAND_TIMEOUT: Final = 10  # seconds

# Rate limiting
MAX_COMMANDS_PER_SECOND: Final = 20
RATE_LIMIT_WINDOW: Final = 1.0  # seconds

# Circuit breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD: Final = 5
CIRCUIT_BREAKER_TIMEOUT: Final = 60  # seconds

# Entity attributes
ATTR_EFFECT_TYPE: Final = "effect_type"
ATTR_SEGMENT_ID: Final = "segment_id"
ATTR_START_LED: Final = "start_led"
ATTR_STOP_LED: Final = "stop_led"
ATTR_LAST_STARTED: Final = "last_started"
ATTR_LAST_STOPPED: Final = "last_stopped"
ATTR_COMMAND_COUNT: Final = "command_count"
ATTR_SUCCESS_COUNT: Final = "success_count"
ATTR_FAILURE_COUNT: Final = "failure_count"
ATTR_SUCCESS_RATE: Final = "success_rate"
ATTR_LAST_ERROR: Final = "last_error"
ATTR_RUNNING_TIME: Final = "running_time"

# Service names
SERVICE_START_EFFECT: Final = "start_effect"
SERVICE_STOP_EFFECT: Final = "stop_effect"
SERVICE_RUN_ONCE: Final = "run_once"
SERVICE_SET_CONFIG: Final = "set_config"
SERVICE_RELOAD: Final = "reload"

# Service fields
SERVICE_FIELD_ENTITY_ID: Final = "entity_id"
SERVICE_FIELD_CONFIG: Final = "config"

# Event types
EVENT_STARTED: Final = f"{DOMAIN}_started"
EVENT_STOPPED: Final = f"{DOMAIN}_stopped"
EVENT_ERROR: Final = f"{DOMAIN}_error"
EVENT_CONFIG_CHANGED: Final = f"{DOMAIN}_config_changed"

# Event data keys
EVENT_DATA_ENTITY_ID: Final = "entity_id"
EVENT_DATA_EFFECT_TYPE: Final = "effect_type"
EVENT_DATA_SEGMENT_ID: Final = "segment_id"
EVENT_DATA_DURATION: Final = "duration"
EVENT_DATA_ERROR: Final = "error"
EVENT_DATA_RECOVERABLE: Final = "recoverable"
EVENT_DATA_OLD_CONFIG: Final = "old_config"
EVENT_DATA_NEW_CONFIG: Final = "new_config"

# State values
STATE_RUNNING: Final = "running"
STATE_STOPPED: Final = "stopped"
STATE_ERROR: Final = "error"

# Icons
ICON_EFFECT: Final = "mdi:led-strip-variant"
ICON_RUNNING: Final = "mdi:play-circle"
ICON_STOPPED: Final = "mdi:stop-circle"
ICON_ERROR: Final = "mdi:alert-circle"
ICON_BRIGHTNESS: Final = "mdi:brightness-6"
ICON_SPEED: Final = "mdi:speedometer"
ICON_SEGMENT: Final = "mdi:view-split-horizontal"
ICON_LED: Final = "mdi:led-on"
ICON_RUN_ONCE: Final = "mdi:play-circle-outline"

# Units
UNIT_BRIGHTNESS: Final = ""  # 0-255 range
UNIT_PERCENT: Final = "%"
UNIT_SECONDS: Final = "s"

# Number entity parameters
NUMBER_BRIGHTNESS_MIN: Final = 0
NUMBER_BRIGHTNESS_MAX: Final = 255
NUMBER_BRIGHTNESS_STEP: Final = 1

NUMBER_SEGMENT_MIN: Final = 0
NUMBER_SEGMENT_MAX: Final = 31
NUMBER_SEGMENT_STEP: Final = 1

NUMBER_LED_MIN: Final = 0
NUMBER_LED_MAX: Final = 1000  # Will be overridden by device capabilities
NUMBER_LED_STEP: Final = 1

# Blend modes for combining multiple inputs
BLEND_MODE_AVERAGE: Final = "average"
BLEND_MODE_MAX: Final = "max"
BLEND_MODE_MIN: Final = "min"
BLEND_MODE_MULTIPLY: Final = "multiply"
BLEND_MODE_ADD: Final = "add"
BLEND_MODES: Final = [
    BLEND_MODE_AVERAGE,
    BLEND_MODE_MAX,
    BLEND_MODE_MIN,
    BLEND_MODE_MULTIPLY,
    BLEND_MODE_ADD,
]

# Trigger types
TRIGGER_TYPE_STATE_CHANGE: Final = "state_change"
TRIGGER_TYPE_THRESHOLD: Final = "threshold"
TRIGGER_TYPE_TIME: Final = "time"
TRIGGER_TYPE_EVENT: Final = "event"
TRIGGER_TYPES: Final = [
    TRIGGER_TYPE_STATE_CHANGE,
    TRIGGER_TYPE_THRESHOLD,
    TRIGGER_TYPE_TIME,
    TRIGGER_TYPE_EVENT,
]

# Transition modes
TRANSITION_MODE_INSTANT: Final = "instant"
TRANSITION_MODE_FADE: Final = "fade"
TRANSITION_MODE_SMOOTH: Final = "smooth"
TRANSITION_MODES: Final = [
    TRANSITION_MODE_INSTANT,
    TRANSITION_MODE_FADE,
    TRANSITION_MODE_SMOOTH,
]

# Zone configuration
CONF_ZONE_COUNT: Final = "zone_count"
CONF_ZONE_SIZE: Final = "zone_size"
CONF_ZONE_OVERLAP: Final = "zone_overlap"

# Effect modulation
CONF_REVERSE_DIRECTION: Final = "reverse_direction"
CONF_FREEZE_ON_MANUAL: Final = "freeze_on_manual"
CONF_TRIGGER_CONFIG: Final = "trigger_config"
CONF_DATA_MAPPING: Final = "data_mapping"
CONF_BLEND_MODE: Final = "blend_mode"
CONF_TRANSITION_MODE: Final = "transition_mode"
CONF_REACTIVE_INPUTS: Final = "reactive_inputs"

# Default values for new features
DEFAULT_REVERSE_DIRECTION: Final = False
DEFAULT_FREEZE_ON_MANUAL: Final = False
DEFAULT_BLEND_MODE: Final = BLEND_MODE_AVERAGE
DEFAULT_TRANSITION_MODE: Final = TRANSITION_MODE_SMOOTH
DEFAULT_ZONE_COUNT: Final = 1

# Logging
LOGGER_NAME: Final = f"custom_components.{DOMAIN}"
