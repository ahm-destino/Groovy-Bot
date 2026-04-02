from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict

_LOCK_TTL_SECONDS = 30 * 60

_inbound_locks: Dict[str, asyncio.Lock] = {}
_outbound_locks: Dict[str, asyncio.Lock] = {}
_lock_last_used: Dict[str, float] = {}


def _get_lock(store: Dict[str, asyncio.Lock], key: str) -> asyncio.Lock:
    lock = store.get(key)
    if not lock:
        lock = asyncio.Lock()
        store[key] = lock
    _lock_last_used[f"{id(store)}:{key}"] = time.time()
    _cleanup()
    return lock


def _cleanup() -> None:
    now = time.time()
    for composite_key, last_used in list(_lock_last_used.items()):
        if now - last_used < _LOCK_TTL_SECONDS:
            continue
        _, key = composite_key.split(":", 1)
        for store in (_inbound_locks, _outbound_locks):
            lock = store.get(key)
            if lock and not lock.locked():
                store.pop(key, None)
        _lock_last_used.pop(composite_key, None)


@asynccontextmanager
async def inbound_phone_lock(phone: str):
    lock = _get_lock(_inbound_locks, phone)
    async with lock:
        yield


@asynccontextmanager
async def outbound_phone_lock(phone: str):
    lock = _get_lock(_outbound_locks, phone)
    async with lock:
        yield
