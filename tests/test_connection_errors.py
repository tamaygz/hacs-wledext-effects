"""Tests for setup-time connection error handling."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.wled_context_effects import __init__ as integration_init
from custom_components.wled_context_effects.const import CONF_EFFECT_TYPE, CONF_WLED_HOST, DOMAIN
from custom_components.wled_context_effects.errors import ConnectionError as IntegrationConnectionError
from custom_components.wled_context_effects.wled_manager import WLEDConnectionManager


@pytest.mark.asyncio
async def test_get_client_wraps_wled_library_connection_error(monkeypatch):
    """get_client should normalize upstream wled connection errors."""

    class LibraryConnectionError(Exception):
        """Simulate wled.exceptions.WLEDConnectionError."""

    class FakeWLEDClient:
        """Minimal client used by the manager."""

        def __init__(self, _host: str) -> None:
            pass

        async def update(self):
            raise LibraryConnectionError("offline")

    monkeypatch.setattr(
        "custom_components.wled_context_effects.wled_manager.WLED",
        FakeWLEDClient,
    )
    monkeypatch.setattr(
        "custom_components.wled_context_effects.wled_manager._WLED_CONNECTION_EXCEPTIONS",
        (LibraryConnectionError,),
    )

    manager = WLEDConnectionManager(MagicMock())
    with pytest.raises(IntegrationConnectionError, match="Failed to connect to WLED device at 1.2.3.4: offline"):
        await manager.get_client("1.2.3.4")


@pytest.mark.asyncio
async def test_setup_logs_connection_not_ready_as_warning(monkeypatch):
    """Setup should log transient WLED connection failures as warning."""

    class FailingConnectionManager:
        """Connection manager that always fails."""

        async def get_client(self, _host: str):
            raise IntegrationConnectionError("Connection timeout for WLED device at 1.2.3.4")

    logger = MagicMock()
    monkeypatch.setattr(integration_init, "_LOGGER", logger)

    hass = SimpleNamespace(data={DOMAIN: {"connection_manager": FailingConnectionManager()}})
    entry = SimpleNamespace(
        title="TextEffect Effect",
        data={CONF_WLED_HOST: "1.2.3.4", CONF_EFFECT_TYPE: "text"},
        options={},
        entry_id="entry-1",
    )

    with pytest.raises(ConfigEntryNotReady, match="Failed to connect to WLED device"):
        await integration_init.async_setup_entry(hass, entry)

    logger.warning.assert_called_once()
    logger.error.assert_not_called()
