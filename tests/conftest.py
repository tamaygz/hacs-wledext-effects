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
_stub("homeassistant.exceptions", HomeAssistantError=_HomeAssistantError)

# homeassistant.core: only Event and HomeAssistant are used
_ha_core = _stub(
    "homeassistant.core",
    HomeAssistant=MagicMock,
    State=object,
    Event=object,
    callback=lambda f: f,
)

# homeassistant.helpers.*
_stub("homeassistant.helpers")
_stub(
    "homeassistant.helpers.event",
    async_track_state_change_event=MagicMock(return_value=MagicMock()),
)
_stub(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=MagicMock,
    UpdateFailed=Exception,
)
_stub("homeassistant.config_entries", ConfigEntry=object)

# --- wled (python-wled external package) ---
_stub("wled", WLED=MagicMock)
