"""HTTP route handlers for the e-waste inference API."""

from __future__ import annotations

import asyncio
import logging
import queue
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, HttpUrl

from config import get_settings
from device_config import device_config
from events import live_bus
from predict import run_prediction
from state import state

logger = logging.getLogger("routes")

router = APIRouter()


class DeviceConfigBody(BaseModel):
    """Payload from the dashboard WiFi / API setup modal."""

    wifi_ssid: str = Field(..., min_length=1, max_length=64)
    wifi_password: str = Field(default="", max_length=64)
    api_base_url: str = Field(
        ...,
        min_length=8,
        max_length=256,
        description="Local or Cloud Run base URL, e.g. http://192.168.1.10:8080",
    )
    capture_interval_ms: int = Field(default=5000, ge=1000, le=60000)


@router.get("/health")
async def health() -> dict:
    """Liveness / readiness style health check."""
    return state.health()


@router.get("/config")
async def public_config() -> dict:
    """Expose non-secret runtime configuration."""
    return get_settings().public_config()


@router.get("/lan-info")
async def lan_info() -> dict:
    """
    Suggest LAN URLs for ESP32 (phone hotspot / home WiFi).

    ESP32 cannot use 127.0.0.1 — it needs this PC's hotspot/LAN IPv4.
    Call this while the PC is already connected to the same hotspot as the camera.
    """
    import socket

    settings = get_settings()
    port = settings.port
    addresses: list[dict[str, str]] = []

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("127."):
                continue
            addresses.append(
                {
                    "ip": ip,
                    "api_base_url": f"http://{ip}:{port}",
                    "predict_url": f"http://{ip}:{port}/predict",
                }
            )
    except OSError as exc:
        logger.warning("lan-info hostname lookup failed: %s", exc)

    # Also probe outbound interface (often the active hotspot/WiFi NIC)
    primary_ip: str | None = None
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        primary_ip = probe.getsockname()[0]
        probe.close()
        if primary_ip and not primary_ip.startswith("127."):
            if not any(a["ip"] == primary_ip for a in addresses):
                addresses.insert(
                    0,
                    {
                        "ip": primary_ip,
                        "api_base_url": f"http://{primary_ip}:{port}",
                        "predict_url": f"http://{primary_ip}:{port}/predict",
                        "primary": "true",
                    },
                )
            else:
                for a in addresses:
                    if a["ip"] == primary_ip:
                        a["primary"] = "true"
    except OSError:
        primary_ip = None

    # Deduplicate by IP
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for a in addresses:
        if a["ip"] in seen:
            continue
        seen.add(a["ip"])
        unique.append(a)

    recommended = next((a for a in unique if a.get("primary") == "true"), unique[0] if unique else None)

    return {
        "port": port,
        "addresses": unique,
        "recommended_api_base_url": recommended["api_base_url"] if recommended else f"http://127.0.0.1:{port}",
        "note": (
            "Connect PC + phone hotspot first, start uvicorn with --host 0.0.0.0, "
            "then use recommended_api_base_url in Device setup (never 127.0.0.1 for ESP32)."
        ),
    }


@router.get("/device-config")
async def get_device_config() -> dict:
    """Return camera provisioning settings (password masked)."""
    return device_config.public_dict(include_password=False)


@router.post("/device-config")
async def set_device_config(body: DeviceConfigBody) -> dict:
    """
    Save WiFi + backend URL from the dashboard popup (in-memory only).

    The dashboard then pushes the same values to the ESP32 SoftAP at
    ``http://192.168.4.1/config`` while the camera is in setup mode.
    """
    raw_url = body.api_base_url.strip()
    if "://" not in raw_url:
        raw_url = f"http://{raw_url}"
    try:
        HttpUrl(raw_url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid api_base_url: {exc}") from exc

    device_config.update(
        wifi_ssid=body.wifi_ssid,
        wifi_password=body.wifi_password,
        api_base_url=raw_url,
        capture_interval_ms=body.capture_interval_ms,
    )
    live_bus.publish({"type": "device_config_updated", "configured": True})
    return {
        "ok": True,
        **device_config.public_dict(include_password=True),
        "instructions": [
            "If the ESP32 is in setup mode, connect your PC to WiFi SSID 'EWaste-Setup'.",
            "Then click 'Push to ESP32' in the dashboard (posts to http://192.168.4.1/config).",
            "The camera saves credentials to flash, joins your WiFi, and POSTs images to api_base_url/predict.",
        ],
    }


@router.get("/latest")
async def latest() -> dict:
    """Return the most recent in-memory inference (for fallback polling)."""
    return state.latest_payload()


@router.get("/events")
async def events() -> StreamingResponse:
    """
    Server-Sent Events stream for live dashboard updates.

    Event types: ``frame`` (scan), ``processing``, ``result`` (conveyor).
    """
    q = live_bus.subscribe()

    async def generate() -> Any:
        try:
            yield live_bus.encode({"type": "connected", "phase": "idle"})
            while True:
                try:
                    event = await asyncio.to_thread(q.get, True, 15.0)
                    yield live_bus.encode(event)
                except queue.Empty:
                    yield ": ping\n\n"
        finally:
            live_bus.unsubscribe(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/predict")
async def predict(file: UploadFile = File(...)) -> dict:
    """
    Accept a multipart image upload from ESP32-CAM, run YOLOv8n, push SSE events.

    Example success:
      {"ewaste": true, "category": "battery", "confidence": 0.983}
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        logger.warning("Unexpected content-type: %s", file.content_type)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    try:
        return await asyncio.to_thread(run_prediction, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Prediction failed")
        state.last_error = str(exc)
        live_bus.publish({"type": "error", "message": str(exc)})
        raise HTTPException(status_code=500, detail="Inference failed") from exc
