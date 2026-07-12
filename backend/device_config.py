"""In-memory ESP32 device configuration (WiFi + API URL). No database."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class DeviceConfig:
    """Credentials and targets entered from the dashboard setup modal."""

    wifi_ssid: str = ""
    wifi_password: str = ""
    api_base_url: str = "http://127.0.0.1:8080"
    capture_interval_ms: int = 5000
    updated_at: float = 0.0

    @property
    def predict_url(self) -> str:
        """Full /predict URL derived from api_base_url."""
        base = self.api_base_url.rstrip("/")
        if base.endswith("/predict"):
            return base
        return f"{base}/predict"


class DeviceConfigStore:
    """Thread-safe in-memory store for camera provisioning settings."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._config = DeviceConfig()

    def get(self) -> DeviceConfig:
        """Return a copy of the current config."""
        with self._lock:
            return DeviceConfig(**asdict(self._config))

    def update(
        self,
        *,
        wifi_ssid: str,
        wifi_password: str,
        api_base_url: str,
        capture_interval_ms: int = 5000,
    ) -> DeviceConfig:
        """Overwrite device config in RAM (empty password keeps previous)."""
        with self._lock:
            password = wifi_password if wifi_password else self._config.wifi_password
            self._config = DeviceConfig(
                wifi_ssid=wifi_ssid.strip(),
                wifi_password=password,
                api_base_url=api_base_url.strip().rstrip("/"),
                capture_interval_ms=max(1000, int(capture_interval_ms)),
                updated_at=time.time(),
            )
            return DeviceConfig(**asdict(self._config))

    def public_dict(self, include_password: bool = False) -> dict[str, Any]:
        """Serialize for API responses (password masked unless requested)."""
        cfg = self.get()
        payload: dict[str, Any] = {
            "wifi_ssid": cfg.wifi_ssid,
            "has_wifi_password": bool(cfg.wifi_password),
            "api_base_url": cfg.api_base_url,
            "predict_url": cfg.predict_url,
            "capture_interval_ms": cfg.capture_interval_ms,
            "updated_at": cfg.updated_at,
            "configured": bool(cfg.wifi_ssid and cfg.api_base_url),
            "esp32_softap_ssid": "EWaste-Setup",
            "esp32_softap_ip": "192.168.4.1",
            "provision_path": "/config",
        }
        if include_password:
            payload["wifi_password"] = cfg.wifi_password
        return payload


device_config = DeviceConfigStore()
