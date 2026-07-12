"""Training and dataset-preparation configuration."""

from __future__ import annotations

import os
from pathlib import Path

# Repository root (parent of train/)
ROOT = Path(__file__).resolve().parent.parent

# Source datasets
DATASET2_DIR = ROOT / "dataset-2"
EWASTE_DIR = ROOT / "ewaste" / "modified-dataset"

# Merged YOLO output
MERGED_DATASET_DIR = ROOT / "dataset"
DATASET_YAML = MERGED_DATASET_DIR / "dataset.yaml"
CLASSES_JSON = MERGED_DATASET_DIR / "classes.json"

# Ultralytics / training
PRETRAINED_WEIGHTS = os.getenv("YOLO_WEIGHTS", "yolov8n.pt")
EPOCHS = int(os.getenv("TRAIN_EPOCHS", "50"))
BATCH = int(os.getenv("TRAIN_BATCH", "16"))
IMGSZ = int(os.getenv("TRAIN_IMGSZ", "640"))
WORKERS = int(os.getenv("TRAIN_WORKERS", "4"))
LR0 = float(os.getenv("TRAIN_LR0", "0.01"))
# Device: auto | cpu | 0 | 0,1  — see train.py resolve_device()
TRAIN_DEVICE = os.getenv("TRAIN_DEVICE", "auto")
TRAIN_REQUIRE_GPU = os.getenv("TRAIN_REQUIRE_GPU", "0") == "1"
PROJECT_DIR = Path(os.getenv("TRAIN_PROJECT", str(Path(__file__).resolve().parent / "runs")))
RUN_NAME = os.getenv("TRAIN_RUN_NAME", "ewaste_yolov8n")
EXPORT_ONNX = os.getenv("TRAIN_EXPORT_ONNX", "0") == "1"

# Where trained weights are copied for inference
BACKEND_MODEL_PATH = ROOT / "backend" / "model" / "best.pt"

# dataset-2 class names (index = class id). Printer appended as id 37.
DATASET2_NAMES: list[str] = [
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
]

EXTRA_CLASS = "Printer"

# Map ewaste folder names → canonical YOLO class names
EWASTE_FOLDER_TO_NAME: dict[str, str] = {
    "Battery": "Battery",
    "Keyboard": "Computer-Keyboard",
    "Microwave": "Microwave",
    "Mobile": "Smartphone",
    "Mouse": "Computer-Mouse",
    "PCB": "PCB",
    "Player": "Music-Player",
    "Printer": "Printer",
    "Television": "Flat-Panel-TV",
    "Washing Machine": "Washing-Machine",
}

# Map classification split folder names to YOLO split names
EWASTE_SPLIT_MAP: dict[str, str] = {
    "train": "train",
    "val": "valid",
    "test": "test",
}


def class_names() -> list[str]:
    """Return ordered class names including Printer."""
    return [*DATASET2_NAMES, EXTRA_CLASS]


def name_to_id() -> dict[str, int]:
    """Map canonical class name → integer id."""
    return {name: idx for idx, name in enumerate(class_names())}


def to_slug(name: str) -> str:
    """Convert a display class name to an API slug."""
    return name.strip().lower().replace(" ", "-")
