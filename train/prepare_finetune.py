"""
Prepare Archive/ ESP32-CAM photos as a SINGLE-CLASS YOLO set: ``ewaste``.

Every image is e-waste — no per-device labels. Each frame gets a full-frame
(inset) bounding box so the model learns “object on conveyor = e-waste”.

Run inside train/.venv:
  python prepare_finetune.py
"""

from __future__ import annotations

import logging
import random
import shutil
from pathlib import Path

import colorlog
import cv2
import numpy as np

import config as cfg

logger = logging.getLogger("prepare_finetune")

ARCHIVE_DIR = cfg.ROOT / "Archive"
OUT_DIR = cfg.ROOT / "dataset-finetune"
FINETUNE_YAML = OUT_DIR / "dataset.yaml"
CLASSES_JSON = OUT_DIR / "classes.json"
SEED = 42
# Inset so Save/X UI in screenshot corners is less of a cue
BOX_INSET = 0.92  # width/height fraction of full frame


def setup_logging() -> None:
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def list_archive_images() -> list[Path]:
    if not ARCHIVE_DIR.is_dir():
        raise SystemExit(f"Missing Archive folder: {ARCHIVE_DIR}")
    imgs = [
        p
        for p in ARCHIVE_DIR.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        and not p.name.startswith("._")
    ]
    imgs.sort(key=lambda p: p.name.encode("utf-8", errors="replace"))
    return imgs


def mask_ui_overlay(bgr: np.ndarray) -> np.ndarray:
    """Cover screenshot Save / X controls in the top-right."""
    h, w = bgr.shape[:2]
    out = bgr.copy()
    x1, y1 = int(w * 0.72), 0
    x2, y2 = w, int(h * 0.16)
    sample_x = max(0, x1 - 8)
    patch = out[y1:y2, sample_x : sample_x + 4]
    if patch.size:
        fill = np.median(patch.reshape(-1, 3), axis=0).astype(np.uint8)
    else:
        fill = np.array([90, 90, 90], dtype=np.uint8)
    out[y1:y2, x1:x2] = fill
    return out


def ewaste_label_line() -> str:
    """Single-class YOLO box: class 0 = ewaste, centered inset frame."""
    # cx cy w h — class id always 0
    return f"0 0.500000 0.500000 {BOX_INSET:.6f} {BOX_INSET:.6f}\n"


def reset_out() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    for split in ("train", "valid"):
        (OUT_DIR / split / "images").mkdir(parents=True, exist_ok=True)
        (OUT_DIR / split / "labels").mkdir(parents=True, exist_ok=True)


def write_yaml() -> None:
    root = OUT_DIR.resolve().as_posix()
    text = "\n".join(
        [
            "# Single-class ESP32-CAM fine-tune set — every object is e-waste",
            f"path: {root}",
            "train: train/images",
            "val: valid/images",
            "",
            "nc: 1",
            "names:",
            "  0: ewaste",
            "",
        ]
    )
    FINETUNE_YAML.write_text(text, encoding="utf-8")


def write_classes_json() -> None:
    import json

    payload = {
        "nc": 1,
        "classes": [{"id": 0, "name": "ewaste", "slug": "ewaste", "ewaste": True}],
        "future_reject_classes": ["plastic", "metal", "glass"],
    }
    text = json.dumps(payload, indent=2) + "\n"
    CLASSES_JSON.write_text(text, encoding="utf-8")
    # Backend should match production single-class head after fine-tune
    (cfg.ROOT / "backend" / "classes.json").write_text(text, encoding="utf-8")


def main() -> None:
    setup_logging()
    images = list_archive_images()
    logger.info("Found %d Archive images — labeling ALL as ewaste=true", len(images))
    if not images:
        raise SystemExit("No images in Archive/")

    reset_out()
    random.seed(SEED)
    indices = list(range(len(images)))
    random.shuffle(indices)
    val_n = max(1, int(len(images) * 0.15))
    val_set = set(indices[:val_n])
    label = ewaste_label_line()

    for i, src in enumerate(images):
        split = "valid" if i in val_set else "train"
        raw = cv2.imdecode(np.fromfile(str(src), dtype=np.uint8), cv2.IMREAD_COLOR)
        if raw is None:
            logger.warning("Skip unreadable image index %d", i)
            continue
        cleaned = mask_ui_overlay(raw)
        stem = f"esp32_{i:04d}"
        out_img = OUT_DIR / split / "images" / f"{stem}.jpg"
        ok, buf = cv2.imencode(".jpg", cleaned, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok:
            continue
        buf.tofile(str(out_img))
        (OUT_DIR / split / "labels" / f"{stem}.txt").write_text(label, encoding="utf-8")

    write_yaml()
    write_classes_json()
    train_n = len(list((OUT_DIR / "train" / "images").glob("*")))
    valid_n = len(list((OUT_DIR / "valid" / "images").glob("*")))
    logger.info(
        "Fine-tune set ready (single class ewaste): train=%d valid=%d → %s",
        train_n,
        valid_n,
        FINETUNE_YAML,
    )
    logger.info("Next: python finetune.py")


if __name__ == "__main__":
    main()
