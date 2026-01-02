"""WLED connection management."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from wled import WLED

from .errors import ConnectionError as WLEDConnectionError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class WLEDConnectionManager:
    """Manage WLED device connections.
    
    This class provides connection pooling and management for WLED devices,
    ensuring efficient reuse of connections and proper cleanup.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the connection manager.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass
        self._clients: dict[str, WLED] = {}
        _LOGGER.debug("WLED connection manager initialized")

    async def get_client(self, host: str) -> WLED:
        """Get or create WLED client for host.

        Args:
            host: WLED device hostname or IP address

        Returns:
            WLED client instance

        Raises:
            WLEDConnectionError: If connection cannot be established
        """
        if host in self._clients:
            _LOGGER.debug("Reusing existing WLED client for %s", host)
            return self._clients[host]

        try:
            _LOGGER.info("Creating new WLED client for %s", host)
            client = WLED(host)

            # Test connection
            await client.update()

            self._clients[host] = client
            return client

        except Exception as err:
            _LOGGER.error("Failed to connect to WLED device at %s: %s", host, err)
            raise WLEDConnectionError(
                f"Failed to connect to WLED device at {host}: {err}"
            ) from err

    async def test_connection(self, host: str) -> bool:
        """Test connection to a WLED device.

        Args:
            host: WLED device hostname or IP address

        Returns:
            True if connection successful
        """
        try:
            client = WLED(host)
            await client.update()
            await client.close()
            return True
        except Exception as err:
            _LOGGER.debug("Connection test failed for %s: %s", host, err)
            return False

    async def close_client(self, host: str) -> None:
        """Close and remove a specific client.

        Args:
            host: WLED device hostname or IP address
        """
        if host in self._clients:
            try:
                _LOGGER.info("Closing WLED client for %s", host)
                await self._clients[host].close()
            except Exception as err:
                _LOGGER.error("Error closing WLED client for %s: %s", host, err)
            finally:
                del self._clients[host]

    async def close_all(self) -> None:
        """Close all connections."""
        _LOGGER.info("Closing all WLED connections (%d clients)", len(self._clients))

        for host, client in list(self._clients.items()):
            try:
                await client.close()
            except Exception as err:
                _LOGGER.error("Error closing WLED client for %s: %s", host, err)

        self._clients.clear()

    @property
    def client_count(self) -> int:
        """Return number of active clients."""
        return len(self._clients)

    def get_connected_hosts(self) -> list[str]:
        """Get list of connected hosts."""
        return list(self._clients.keys())
