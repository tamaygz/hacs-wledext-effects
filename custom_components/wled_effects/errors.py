"""Exceptions for WLED Effects integration."""
from homeassistant.exceptions import HomeAssistantError


class WLEDEffectsException(HomeAssistantError):
    """Base exception for WLED Effects integration."""


class ConfigurationError(WLEDEffectsException):
    """Exception raised for configuration validation errors.
    
    Use this when:
    - Invalid effect configuration
    - Invalid LED range
    - Invalid segment ID
    - Invalid parameter values
    """


class ConnectionError(WLEDEffectsException):
    """Exception raised for WLED device communication errors.
    
    Use this when:
    - WLED device unreachable
    - Network timeout
    - Connection refused
    - API errors
    """


class EffectExecutionError(WLEDEffectsException):
    """Exception raised for effect runtime errors.
    
    Use this when:
    - Effect code throws exception
    - Invalid effect state
    - Effect initialization failure
    """


class StateSourceError(WLEDEffectsException):
    """Exception raised for state source entity errors.
    
    Use this when:
    - State source entity not found
    - State source entity unavailable
    - Invalid state value
    - Attribute not found
    """


class EffectNotFoundError(WLEDEffectsException):
    """Exception raised when effect type is not registered.
    
    Use this when:
    - Requested effect type doesn't exist
    - Effect failed to load/register
    """


class DeviceNotFoundError(WLEDEffectsException):
    """Exception raised when WLED device is not found.
    
    Use this when:
    - WLED device ID not in registry
    - WLED integration not loaded
    """


class RateLimitError(WLEDEffectsException):
    """Exception raised when rate limit is exceeded.
    
    Use this when:
    - Too many commands sent
    - Rate limiter blocks request
    """


class CircuitBreakerOpenError(WLEDEffectsException):
    """Exception raised when circuit breaker is open.
    
    Use this when:
    - Circuit breaker prevents operation
    - Too many recent failures
    """
