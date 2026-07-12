"""Load YOLOv8 weights once at process startup."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import torch
from ultralytics import YOLO

from config import Settings, get_settings
from state import state

logger = logging.getLogger("model_loader")

_model: YOLO | None = None
_device: str | int = "cpu"


def resolve_device(preferred: str) -> str | int:
    """Resolve inference device from settings."""
    if preferred == "auto":
        if torch.cuda.is_available():
            logger.info("Inference device: CUDA GPU")
            return 0
        logger.info("Inference device: CPU")
        return "cpu"
    if preferred.isdigit():
        return int(preferred)
    return preferred


def load_model(settings: Settings | None = None) -> YOLO:
    """
    Load best.pt once. Raises FileNotFoundError if weights are missing.

    The backend never trains — only inference weights are loaded.
    """
    global _model, _device

    settings = settings or get_settings()
    path = Path(settings.model_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Model weights not found at {path}. "
            "Train locally with train/train.py so best.pt is copied to backend/model/."
        )

    _device = resolve_device(settings.device)
    logger.info("Loading YOLO model from %s (device=%s)", path, _device)
    _model = YOLO(str(path))
    # Warm-up run with a tiny blank image is skipped; first request initializes CUDA kernels.
    state.mark_model_loaded(str(path))
    logger.info("Model loaded successfully")
    return _model


def get_model() -> YOLO:
    """Return the loaded model or raise if not initialized."""
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() during startup.")
    return _model


def get_device() -> str | int:
    """Return the resolved inference device."""
    return _device


def predict_raw(image_bgr: Any, imgsz: int, conf: float) -> Any:
    """Run Ultralytics predict and return the first Results object."""
    model = get_model()
    results = model.predict(
        source=image_bgr,
        imgsz=imgsz,
        conf=conf,
        device=get_device(),
        verbose=False,
    )
    return results[0]
