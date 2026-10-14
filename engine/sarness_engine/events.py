"""In-process publish/subscribe bus feeding the ``/v1/events`` WebSocket."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

log = logging.getLogger("sarness.events")


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def _deliver(self, event: dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Slow consumer: drop progress/preview events first, never terminal states.
                if event["type"] in ("job.progress", "job.preview", "system.stats", "download.progress"):
                    continue
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:  # pragma: no cover - defensive
                    pass

    def publish(self, type_: str, data: dict[str, Any]) -> None:
        """Thread-safe publish; may be called from worker/reader threads."""
        event = {"type": type_, "ts": time.time(), "data": data}
        loop = self._loop
        if loop is None:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            self._deliver(event)
        else:
            loop.call_soon_threadsafe(self._deliver, event)
