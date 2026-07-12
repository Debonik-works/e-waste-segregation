"""Central configuration for the FastAPI inference backend."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
# Prefer backend/classes.json (Docker-friendly); fall back to merged dataset path.
_BACKEND_CLASSES = BACKEND_DIR / "classes.json"
_DATASET_CLASSES = ROOT_DIR / "dataset" / "classes.json"
DEFAULT_CLASSES_JSON = _BACKEND_CLASSES if _BACKEND_CLASSES.is_file() else _DATASET_CLASSES


def _default_class_slugs() -> list[str]:
    """Load class slugs from classes.json when available."""
    path = Path(os.getenv("CLASSES_JSON", str(DEFAULT_CLASSES_JSON)))
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return [c["slug"] for c in data.get("classes", [])]
    # Fallback matching train/config.py order (38 classes)
    names = [
        "Battery",
        "Blood-Pressure-Monitor",
        "Boiler",
        "Clothes-Iron",
        "Coffee-Machine",
        "Computer-Keyboard",
        "Computer-Mouse",
        "Cooling-Display",
        "Desktop-PC",
        "Digital-Oscilloscope",
        "Drone",
        "Electric-Guitar",
        "Electronic-Keyboard",
        "Flashlight",
        "Flat-Panel-Monitor",
        "Flat-Panel-TV",
        "Glucose-Meter",
        "HDD",
        "Laptop",
        "Microwave",
        "Music-Player",
        "Oven",
        "PCB",
        "Photovoltaic-Panel",
        "Projector",
        "Refrigerator",
        "Rotary-Mower",
        "Router",
        "Server",
        "Smartphone",
        "Smoke-Detector",
        "Straight-Tube-Fluorescent-Lamp",
        "Street-Lamp",
        "TV-Remote-Control",
        "Telephone-Set",
        "USB-Flash-Drive",
        "Washing-Machine",
        "Printer",
    ]
    return [n.lower().replace(" ", "-") for n in names]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8080, alias="PORT")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # Model / inference
    model_path: str = Field(
        default=str(BACKEND_DIR / "model" / "best.pt"),
        alias="MODEL_PATH",
    )
    confidence_threshold: float = Field(default=0.50, alias="CONFIDENCE_THRESHOLD")
    inference_imgsz: int = Field(default=640, alias="INFERENCE_IMGSZ")
    device: str = Field(default="auto", alias="INFERENCE_DEVICE")

    # Classes
    classes_json: str = Field(default=str(DEFAULT_CLASSES_JSON), alias="CLASSES_JSON")
    allowed_classes: str = Field(default="", alias="ALLOWED_CLASSES")
    future_reject_classes: str = Field(
        default="plastic,metal,glass",
        alias="FUTURE_REJECT_CLASSES",
    )

    # Serial (local only — disabled on Cloud Run)
    serial_enabled: bool = Field(default=False, alias="SERIAL_ENABLED")
    serial_port: str = Field(default="", alias="SERIAL_PORT")
    serial_baud: int = Field(default=9600, alias="SERIAL_BAUD")
    serial_timeout: float = Field(default=2.0, alias="SERIAL_TIMEOUT")
    serial_retries: int = Field(default=3, alias="SERIAL_RETRIES")
    motor_duration_ms: int = Field(default=1500, alias="MOTOR_DURATION_MS")
    motor_speed: int = Field(default=200, alias="MOTOR_SPEED")

    def cors_origin_list(self) -> list[str]:
        """Parse CORS origins CSV."""
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def allowed_class_list(self) -> list[str]:
        """Return allowed category slugs (empty ALLOWED_CLASSES → all known)."""
        if self.allowed_classes.strip():
            return [c.strip().lower() for c in self.allowed_classes.split(",") if c.strip()]
        return _default_class_slugs()

    def class_id_to_slug(self) -> dict[int, str]:
        """Map YOLO class index → slug."""
        path = Path(self.classes_json)
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return {int(c["id"]): str(c["slug"]) for c in data.get("classes", [])}
        slugs = _default_class_slugs()
        return {i: s for i, s in enumerate(slugs)}

    def public_config(self) -> dict[str, Any]:
        """Non-secret config for GET /config."""
        return {
            "confidence_threshold": self.confidence_threshold,
            "inference_imgsz": self.inference_imgsz,
            "serial_enabled": self.serial_enabled,
            "motor_duration_ms": self.motor_duration_ms,
            "motor_speed": self.motor_speed,
            "allowed_classes": self.allowed_class_list(),
            "future_reject_classes": [
                c.strip() for c in self.future_reject_classes.split(",") if c.strip()
            ],
            "model_path": self.model_path,
        }


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
