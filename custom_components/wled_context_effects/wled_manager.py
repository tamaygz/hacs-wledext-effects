"""WLED connection management."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING, Any, Callable

from wled import WLED, Device, WLEDConnectionClosedError

from .const import (
    WS_RECONNECT_BACKOFF_MAX,
    WS_RECONNECT_BACKOFF_MIN,
    WS_SAFETY_POLL_INTERVAL,
)
from .errors import ConnectionError as WLEDConnectionError
from .wled_json_api import WLEDJsonApiClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    import aiohttp

_LOGGER = logging.getLogger(__name__)

# Separate capacity limits per pool to prevent cross-pool eviction
MAX_CACHED_WLED_CLIENTS = 10
MAX_CACHED_JSON_CLIENTS = 10


class WLEDDeviceStateCache:
    """Push-based cache of a WLED device's full state via WebSocket.

    Wraps a single ``wled.WLED`` client per host. ``wled.listen()`` streams
    ``Device`` snapshots which are stored in ``self.device``. A low-frequency
    safety poll calls ``wled.update()`` to compensate for WLED issue #2026
    (non-main-segment state changes are not always pushed).

    Lifecycle is ref-counted via ``acquire()`` / ``release()`` on
    ``WLEDConnectionManager`` so several effects on the same host share one
    WebSocket.
    """

    def __init__(self, host: str, wled_client: WLED) -> None:
        self.host = host
        self._wled = wled_client
        self.device: Device | None = None
        self._listeners: list[Callable[[Device], None]] = []
        self._listen_task: asyncio.Task[None] | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._stopping = False
        self._ref_count = 0
        self._ready = asyncio.Event()

    @property
    def ref_count(self) -> int:
        return self._ref_count

    def increment(self) -> None:
        self._ref_count += 1

    def decrement(self) -> int:
        self._ref_count = max(0, self._ref_count - 1)
        return self._ref_count

    def add_listener(self, callback: Callable[[Device], None]) -> Callable[[], None]:
        """Register a callback fired on every Device update. Returns an unsubscribe fn."""
        self._listeners.append(callback)

        def _remove() -> None:
            try:
                self._listeners.remove(callback)
            except ValueError:
                pass

        return _remove

    async def start(self) -> None:
        """Open the WebSocket and start the listen + safety-poll background tasks."""
        if self._listen_task is not None:
            return

        # Seed with one HTTP fetch so consumers have data immediately.
        # Route through _on_device so any listeners registered before start()
        # receive the initial snapshot and _ready is set consistently.
        try:
            device = await self._wled.update()
            self._on_device(device)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Initial state fetch for %s failed: %s", self.host, err)

        self._stopping = False
        self._listen_task = asyncio.create_task(
            self._listen_loop(), name=f"wled-listen-{self.host}"
        )
        self._poll_task = asyncio.create_task(
            self._safety_poll_loop(), name=f"wled-safety-poll-{self.host}"
        )
        _LOGGER.info("WLED WebSocket cache started for %s", self.host)

    async def stop(self) -> None:
        """Cancel background tasks and close the WLED client."""
        self._stopping = True
        for task in (self._listen_task, self._poll_task):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
        self._listen_task = None
        self._poll_task = None
        try:
            await self._wled.disconnect()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Error disconnecting WLED WS for %s: %s", self.host, err)
        _LOGGER.info("WLED WebSocket cache stopped for %s", self.host)

    async def wait_ready(self, timeout: float = 5.0) -> bool:
        """Wait until at least one Device snapshot has been received."""
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def get_state_dict(self) -> dict[str, Any]:
        """Return a state dict matching the shape of ``json_client.get_state()``.

        Only includes fields consumed by this integration (``on``, ``bri``).
        Returns an empty dict if no snapshot has arrived yet.
        """
        if self.device is None or self.device.state is None:
            return {}
        state = self.device.state
        return {
            "on": bool(getattr(state, "on", False)),
            "bri": int(getattr(state, "brightness", 0)),
        }

    def _on_device(self, device: Device) -> None:
        self.device = device
        if not self._ready.is_set():
            self._ready.set()
        for cb in list(self._listeners):
            try:
                cb(device)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("WLED listener callback raised: %s", err)

    async def _listen_loop(self) -> None:
        """Maintain the WebSocket connection with exponential backoff reconnects."""
        backoff = WS_RECONNECT_BACKOFF_MIN
        while not self._stopping:
            try:
                if not self._wled.connected:
                    await self._wled.connect()
                _LOGGER.debug("WLED WebSocket connected: %s", self.host)
                backoff = WS_RECONNECT_BACKOFF_MIN
                await self._wled.listen(callback=self._on_device)
            except asyncio.CancelledError:
                raise
            except WLEDConnectionClosedError as err:
                if self._stopping:
                    return
                _LOGGER.info("WLED WS closed for %s: %s", self.host, err)
            except Exception as err:  # noqa: BLE001
                if self._stopping:
                    return
                _LOGGER.warning("WLED WS error for %s: %s", self.host, err)

            if self._stopping:
                return
            jitter = random.uniform(-backoff * 0.25, backoff * 0.25)
            sleep_time = min(backoff + jitter, WS_RECONNECT_BACKOFF_MAX)
            await asyncio.sleep(sleep_time)
            backoff = min(backoff * 2, WS_RECONNECT_BACKOFF_MAX)

    async def _safety_poll_loop(self) -> None:
        """Periodic HTTP refresh to mitigate WLED issue #2026 push gaps."""
        while not self._stopping:
            try:
                await asyncio.sleep(WS_SAFETY_POLL_INTERVAL)
                device = await self._wled.update()
                if device is not None:
                    self._on_device(device)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("WLED safety poll error for %s: %s", self.host, err)


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
        self._state_caches: dict[str, WLEDDeviceStateCache] = {}
        # Serialises acquire_state_cache so concurrent setups for the same host
        # never create duplicate caches.
        self._state_cache_lock: asyncio.Lock = asyncio.Lock()
        _LOGGER.debug("WLED connection manager initialized")

    async def acquire_state_cache(self, host: str) -> WLEDDeviceStateCache:
        """Get or create a push-based state cache for ``host`` and bump its refcount.

        Callers MUST pair this with ``release_state_cache(host)`` on unload so the
        underlying WebSocket is closed when no effect needs it anymore.

        A lock serialises concurrent callers for the same host so only one cache
        is ever created/started per host.
        """
        async with self._state_cache_lock:
            cache = self._state_caches.get(host)
            if cache is None:
                wled_client = await self.get_client(host)
                cache = WLEDDeviceStateCache(host, wled_client)
                self._state_caches[host] = cache
                await cache.start()
            cache.increment()
            return cache

    async def release_state_cache(self, host: str) -> None:
        """Decrement refcount; stop the WS when it reaches zero.

        Uses the same lock as ``acquire_state_cache`` so a concurrent acquire
        and release for the same host cannot race on the refcount.
        """
        async with self._state_cache_lock:
            cache = self._state_caches.get(host)
            if cache is None:
                return
            if cache.decrement() == 0:
                self._state_caches.pop(host, None)
                await cache.stop()

    def get_state_cache(self, host: str) -> WLEDDeviceStateCache | None:
        """Return the active state cache for ``host`` without changing refcount."""
        return self._state_caches.get(host)

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

        # Evict from WLED pool only — never touch the JSON client pool.
        # Skip hosts that have an active state cache; evicting their client would
        # tear down the WebSocket and break all consumers.
        if len(self._clients) >= MAX_CACHED_WLED_CLIENTS:
            evicted = False
            for oldest_host in list(self._clients):
                if oldest_host not in self._state_caches:
                    _LOGGER.info(
                        "WLED client cache full (%d), evicting oldest: %s",
                        MAX_CACHED_WLED_CLIENTS,
                        oldest_host,
                    )
                    await self.close_client(oldest_host)
                    evicted = True
                    break
            if not evicted:
                # All cached clients have active state caches. Look for an
                # inactive one (ref_count == 0) to evict safely without
                # breaking running effects.
                lru_inactive_host = None
                for candidate in list(self._clients):
                    candidate_cache = self._state_caches.get(candidate)
                    if candidate_cache is None or candidate_cache.ref_count == 0:
                        lru_inactive_host = candidate
                        break

                if lru_inactive_host is not None:
                    _LOGGER.warning(
                        "WLED client cache full (%d); evicting inactive "
                        "cache+client pair for %s to make room for %s",
                        MAX_CACHED_WLED_CLIENTS,
                        lru_inactive_host,
                        host,
                    )
                    lru_cache = self._state_caches.pop(lru_inactive_host, None)
                    if lru_cache is not None:
                        await lru_cache.stop()
                    await self.close_client(lru_inactive_host)
                else:
                    # Every cached client has an active state cache (ref_count > 0).
                    # Refuse to evict to avoid breaking running effects; log a
                    # clear error and allow the pool to grow past the soft cap.
                    _LOGGER.error(
                        "WLED client cache full (%d) and all %d cached clients have "
                        "active state caches (ref_count > 0); cannot safely evict. "
                        "Creating new client for %s beyond the soft cap.",
                        MAX_CACHED_WLED_CLIENTS,
                        len(self._clients),
                        host,
                    )

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
        client = WLED(host)
        try:
            await client.update()
            return True
        except (WLEDConnectionError, OSError, asyncio.TimeoutError, ValueError) as err:
            _LOGGER.debug("Connection test failed for %s: %s", host, err)
            return False
        finally:
            try:
                await client.close()
            except Exception:
                pass

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

        # Evict from JSON pool only — never touch the WLED client pool
        if len(self._json_clients) >= MAX_CACHED_JSON_CLIENTS:
            oldest_key = next(iter(self._json_clients))
            _LOGGER.info(
                "JSON client cache full (%d), evicting oldest: %s",
                MAX_CACHED_JSON_CLIENTS,
                oldest_key,
            )
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

        # Stop state caches first so listen tasks don't fight with client.close()
        for host, cache in list(self._state_caches.items()):
            try:
                await cache.stop()
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Error stopping state cache for %s: %s", host, err)
        self._state_caches.clear()

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
