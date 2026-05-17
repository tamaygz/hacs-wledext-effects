"""Pytest configuration: inject HA and third-party stubs so tests run without HA installed."""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock


def _stub(name: str, **attrs) -> ModuleType:
    """Create and register a stub module."""
    m = ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


# --- homeassistant.exceptions ---
class _HomeAssistantError(Exception):
    """Stub for HomeAssistantError."""


# Hierarchy of stubs required by the integration's import chain
_stub("homeassistant")


class _Platform(str):
    """Stub for homeassistant.const.Platform enum-like values."""

    BUTTON = "button"
    NUMBER = "number"
    SELECT = "select"
    SENSOR = "sensor"
    SWITCH = "switch"


_stub(
    "homeassistant.const",
    Platform=_Platform,
    CONF_HOST="host",
    CONF_NAME="name",
    CONF_PORT="port",
    EVENT_HOMEASSISTANT_STOP="homeassistant_stop",
)
_stub(
    "homeassistant.exceptions",
    HomeAssistantError=_HomeAssistantError,
    ConfigEntryNotReady=_HomeAssistantError,
)

# homeassistant.core: only Event and HomeAssistant are used
_ha_core = _stub(
    "homeassistant.core",
    HomeAssistant=MagicMock,
    State=object,
    Event=object,
    callback=lambda f: f,
)

# homeassistant.helpers.*
_stub("homeassistant.helpers", device_registry=MagicMock())
_stub(
    "homeassistant.helpers.event",
    async_track_state_change_event=MagicMock(return_value=MagicMock()),
)
class _SubscriptableMock:
    """A class that supports __class_getitem__ for generic-style subscripting."""

    def __class_getitem__(cls, item):  # noqa: D105
        return cls

    def __init__(self, *args, **kwargs) -> None:  # noqa: D107
        pass

    def __getattr__(self, name):  # noqa: D105
        return MagicMock()


_stub(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=_SubscriptableMock,
    UpdateFailed=Exception,
)
_stub("homeassistant.config_entries", ConfigEntry=object)

# --- wled (python-wled external package) ---
_stub(
    "wled",
    WLED=MagicMock,
    Device=MagicMock,
    WLEDConnectionClosedError=type("WLEDConnectionClosedError", (Exception,), {}),
)
