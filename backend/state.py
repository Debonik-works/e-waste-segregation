"""In-memory store for the latest inference result (no database)."""

from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LatestInference:
    """Snapshot of the most recent prediction (or in-flight scan)."""

    request_id: str = ""
    timestamp: float = 0.0
    phase: str = "idle"  # idle | scan | process | result
    ewaste: bool = False
    category: str = "unknown"
    confidence: float = 0.0
    inference_ms: float = 0.0
    serial_command: str | None = None
    serial_status: str | None = None
    original_jpeg: bytes = b""
    annotated_jpeg: bytes = b""
    detections: list[dict[str, Any]] = field(default_factory=list)


class AppState:
    """Thread-safe process-wide application state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started_at: float = time.time()
        self.request_count: int = 0
        self.model_loaded: bool = False
        self.model_path: str = ""
        self.latest: LatestInference = LatestInference()
        self.last_error: str | None = None

    def mark_model_loaded(self, path: str) -> None:
        """Record successful model load."""
        with self._lock:
            self.model_loaded = True
            self.model_path = path

    def increment_requests(self) -> int:
        """Bump request counter; return new value."""
        with self._lock:
            self.request_count += 1
            return self.request_count

    def set_latest(self, latest: LatestInference) -> None:
        """Overwrite the in-memory latest inference (no history)."""
        with self._lock:
            self.latest = latest

    def patch_latest(self, **kwargs: Any) -> LatestInference:
        """Update fields on the current latest snapshot."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.latest, key):
                    setattr(self.latest, key, value)
            return self.latest

    def get_latest(self) -> LatestInference:
        """Return a shallow copy-safe reference to latest."""
        with self._lock:
            return self.latest

    def health(self) -> dict[str, Any]:
        """Build health payload."""
        with self._lock:
            uptime = time.time() - self.started_at
            fps = self.request_count / uptime if uptime > 0 else 0.0
            return {
                "status": "ok" if self.model_loaded else "degraded",
                "model_loaded": self.model_loaded,
                "model_path": self.model_path,
                "uptime_seconds": round(uptime, 2),
                "request_count": self.request_count,
                "approx_fps": round(fps, 3),
                "last_error": self.last_error,
                "has_latest": bool(self.latest.request_id),
                "phase": self.latest.phase,
            }

    def latest_payload(self) -> dict[str, Any]:
        """Serialize latest inference for GET /latest."""
        with self._lock:
            latest = self.latest
            if not latest.request_id:
                return {
                    "available": False,
                    "message": "No inference yet",
                    "phase": "idle",
                }

            def b64(data: bytes) -> str | None:
                if not data:
                    return None
                return base64.b64encode(data).decode("ascii")

            return {
                "available": True,
                "request_id": latest.request_id,
                "timestamp": latest.timestamp,
                "phase": latest.phase,
                "ewaste": latest.ewaste,
                "category": latest.category,
                "confidence": latest.confidence,
                "inference_ms": latest.inference_ms,
                "serial_command": latest.serial_command,
                "serial_status": latest.serial_status,
                "detections": latest.detections,
                "original_image_b64": b64(latest.original_jpeg),
                "annotated_image_b64": b64(latest.annotated_jpeg),
                "request_count": self.request_count,
            }


# Process singleton
state = AppState()
