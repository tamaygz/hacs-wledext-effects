"""WLED connection management."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from wled import WLED

from .errors import ConnectionError as WLEDConnectionError
from .wled_json_api import WLEDJsonApiClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    import aiohttp

_LOGGER = logging.getLogger(__name__)

# Maximum number of cached clients to prevent unbounded memory growth
MAX_CACHED_CLIENTS = 20


class WLEDConnectionManager:
    """Manage WLED device connections.
    
    This class provides connection pooling and management for WLED devices,
    ensuring efficient reuse of connections and proper cleanup.
    Manages both python-wled clients and JSON API clients.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the connection manager.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass
        self._clients: dict[str, WLED] = {}
        self._json_clients: dict[str, WLEDJsonApiClient] = {}
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
            # Move to end (LRU)
            client = self._clients.pop(host)
            self._clients[host] = client
            return client

        # Check if at capacity and evict oldest
        total_clients = len(self._clients) + len(self._json_clients)
        if total_clients >= MAX_CACHED_CLIENTS:
            # Evict oldest python-wled client
            if self._clients:
                oldest_host = next(iter(self._clients))
                _LOGGER.info("Client cache full (%d), evicting oldest: %s", MAX_CACHED_CLIENTS, oldest_host)
                await self.close_client(oldest_host)

        try:
            _LOGGER.info("Creating new WLED client for %s", host)
            client = WLED(host)

            # Test connection with timeout
            try:
                await asyncio.wait_for(client.update(), timeout=10.0)
            except asyncio.TimeoutError:
                await client.close()
                raise WLEDConnectionError(
                    f"Connection timeout for WLED device at {host}"
                )

            self._clients[host] = client
            return client

        except WLEDConnectionError:
            raise
        except (OSError, asyncio.TimeoutError, ValueError) as err:
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

    async def get_json_client(
        self,
        host: str,
        port: int = 80,
        session: aiohttp.ClientSession | None = None,
    ) -> WLEDJsonApiClient:
        """Get or create JSON API client for host.

        Args:
            host: WLED device hostname or IP address
            port: HTTP port (default 80)
            session: Optional aiohttp session to reuse

        Returns:
            WLEDJsonApiClient instance

        Raises:
            WLEDConnectionError: If connection cannot be established
        """
        client_key = f"{host}:{port}"
        
        if client_key in self._json_clients:
            _LOGGER.debug("Reusing existing JSON API client for %s", client_key)
            # Move to end (LRU)
            client = self._json_clients.pop(client_key)
            self._json_clients[client_key] = client
            return client

        # Check if at capacity and evict oldest
        total_clients = len(self._clients) + len(self._json_clients)
        if total_clients >= MAX_CACHED_CLIENTS:
            # Evict oldest JSON API client
            if self._json_clients:
                oldest_key = next(iter(self._json_clients))
                _LOGGER.info("Client cache full (%d), evicting oldest: %s", MAX_CACHED_CLIENTS, oldest_key)
                parts = oldest_key.split(":")
                await self.close_json_client(parts[0], int(parts[1]) if len(parts) > 1 else 80)

        try:
            _LOGGER.info("Creating new JSON API client for %s", client_key)
            client = WLEDJsonApiClient(host, port, session)

            # Test connection with timeout
            try:
                await asyncio.wait_for(client.get_state(), timeout=10.0)
            except asyncio.TimeoutError:
                await client.close()
                raise WLEDConnectionError(
                    f"Connection timeout for WLED device at {client_key}"
                )

            self._json_clients[client_key] = client
            return client

        except WLEDConnectionError:
            raise
        except (OSError, asyncio.TimeoutError, ValueError) as err:
            _LOGGER.error("Failed to connect to WLED device at %s: %s", client_key, err)
            raise WLEDConnectionError(
                f"Failed to connect to WLED device at {client_key}: {err}"
            ) from err

    async def close_json_client(self, host: str, port: int = 80) -> None:
        """Close and remove a specific JSON API client.

        Args:
            host: WLED device hostname or IP address
            port: HTTP port (default 80)
        """
        client_key = f"{host}:{port}"
        
        if client_key in self._json_clients:
            try:
                _LOGGER.info("Closing JSON API client for %s", client_key)
                await self._json_clients[client_key].close()
            except Exception as err:
                _LOGGER.error("Error closing JSON API client for %s: %s", client_key, err)
            finally:
                del self._json_clients[client_key]

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
        total_clients = len(self._clients) + len(self._json_clients)
        _LOGGER.info("Closing all WLED connections (%d clients)", total_clients)

        # Close python-wled clients
        for host, client in list(self._clients.items()):
            try:
                await client.close()
            except Exception as err:
                _LOGGER.error("Error closing WLED client for %s: %s", host, err)

        # Close JSON API clients
        for client_key, client in list(self._json_clients.items()):
            try:
                await client.close()
            except Exception as err:
                _LOGGER.error("Error closing JSON API client for %s: %s", client_key, err)

        self._clients.clear()
        self._json_clients.clear()

    @property
    def client_count(self) -> int:
        """Return number of active clients."""
        return len(self._clients) + len(self._json_clients)

    def get_connected_hosts(self) -> list[str]:
        """Get list of connected hosts."""
        hosts = set(self._clients.keys())
        # Extract host from "host:port" keys in JSON clients
        for key in self._json_clients.keys():
            host = key.split(":")[0]
            hosts.add(host)
        return list(hosts)
