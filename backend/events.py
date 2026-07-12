"""Thread-safe pub/sub bus for Server-Sent Events to the dashboard."""

from __future__ import annotations

import json
import logging
import queue
import threading
from typing import Any

logger = logging.getLogger("events")


class LiveBus:
    """Fan-out live events (scan → process → result) to all SSE subscribers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue[dict[str, Any]]] = []

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        """Register a new subscriber queue."""
        q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=64)
        with self._lock:
            self._subscribers.append(q)
        logger.info("SSE subscriber connected (%d total)", len(self._subscribers))
        return q

    def unsubscribe(self, q: queue.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber queue."""
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)
        logger.info("SSE subscriber disconnected (%d total)", len(self._subscribers))

    def publish(self, event: dict[str, Any]) -> None:
        """Publish an event to all subscribers (non-blocking)."""
        dead: list[queue.Queue[dict[str, Any]]] = []
        with self._lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                dead.append(q)
                logger.warning("Dropping slow SSE subscriber (queue full)")
        for q in dead:
            self.unsubscribe(q)

    @staticmethod
    def encode(event: dict[str, Any]) -> str:
        """Encode one SSE data frame."""
        return f"data: {json.dumps(event, separators=(',', ':'))}\n\n"


live_bus = LiveBus()
