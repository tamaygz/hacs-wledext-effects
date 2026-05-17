"""Tests for WLEDDeviceStateCache (push-based WebSocket cache)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.wled_context_effects.wled_manager import (
    WLEDDeviceStateCache,
)


def _make_device(on: bool = True, brightness: int = 128, leds_count: int = 30):
    return SimpleNamespace(
        state=SimpleNamespace(on=on, brightness=brightness),
        info=SimpleNamespace(leds=SimpleNamespace(count=leds_count), effects=["Solid"]),
    )


@pytest.fixture
def wled_client():
    client = MagicMock()
    client.connected = False
    client.update = AsyncMock(return_value=_make_device())
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    # listen() blocks forever in production; emulate by awaiting an Event.
    client._listen_event = asyncio.Event()

    async def _listen(callback):
        await client._listen_event.wait()

    client.listen = AsyncMock(side_effect=_listen)
    return client


@pytest.mark.asyncio
async def test_start_seeds_initial_state(wled_client):
    cache = WLEDDeviceStateCache("1.2.3.4", wled_client)
    await cache.start()
    try:
        assert await cache.wait_ready(timeout=0.5)
        assert cache.get_state_dict() == {"on": True, "bri": 128}
    finally:
        wled_client._listen_event.set()
        await cache.stop()


@pytest.mark.asyncio
async def test_get_state_dict_empty_without_data(wled_client):
    wled_client.update = AsyncMock(side_effect=RuntimeError("offline"))
    cache = WLEDDeviceStateCache("1.2.3.4", wled_client)
    await cache.start()
    try:
        # Initial fetch failed and listen() hasn't pushed → empty dict.
        assert cache.get_state_dict() == {}
    finally:
        wled_client._listen_event.set()
        await cache.stop()


@pytest.mark.asyncio
async def test_refcount(wled_client):
    cache = WLEDDeviceStateCache("h", wled_client)
    assert cache.ref_count == 0
    cache.increment()
    cache.increment()
    assert cache.ref_count == 2
    assert cache.decrement() == 1
    assert cache.decrement() == 0
    # decrement below zero clamps
    assert cache.decrement() == 0


@pytest.mark.asyncio
async def test_listener_fanout(wled_client):
    cache = WLEDDeviceStateCache("h", wled_client)
    received = []
    unsub = cache.add_listener(lambda d: received.append(d))
    await cache.start()
    try:
        # Initial seed fires listeners via _on_device path? No — start() sets
        # device directly via update(). Manually trigger to test fan-out.
        new_dev = _make_device(on=False, brightness=42)
        cache._on_device(new_dev)
        assert received[-1] is new_dev
        assert cache.get_state_dict() == {"on": False, "bri": 42}
        unsub()
        cache._on_device(_make_device())
        # No new entry appended after unsub
        assert received[-1] is new_dev
    finally:
        wled_client._listen_event.set()
        await cache.stop()


@pytest.mark.asyncio
async def test_stop_cancels_tasks(wled_client):
    cache = WLEDDeviceStateCache("h", wled_client)
    await cache.start()
    listen_task = cache._listen_task
    poll_task = cache._poll_task
    assert listen_task is not None and poll_task is not None
    await cache.stop()
    assert listen_task.done()
    assert poll_task.done()
    wled_client.disconnect.assert_awaited()
