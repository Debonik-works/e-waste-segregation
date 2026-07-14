"""
Fine-tune backend/model/best.pt as a SINGLE-CLASS e-waste detector on Archive/.

Continues from best.pt weights (backbone transfer). Detect head becomes nc=1
(``ewaste``). Does not retrain the original 38-class corpus from scratch.

Prerequisites (train/.venv):
  python prepare_finetune.py
  python finetune.py
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import colorlog
import torch
from ultralytics import YOLO

import config as cfg

logger = logging.getLogger("finetune")

FINETUNE_YAML = cfg.ROOT / "dataset-finetune" / "dataset.yaml"
# Continue from current production weights (binary ewaste) when present
SOURCE_WEIGHTS = Path(os.getenv("FINETUNE_WEIGHTS", str(cfg.BACKEND_MODEL_PATH)))
EPOCHS = int(os.getenv("FINETUNE_EPOCHS", "80"))
BATCH = int(os.getenv("FINETUNE_BATCH", "8"))
IMGSZ = int(os.getenv("FINETUNE_IMGSZ", str(cfg.IMGSZ)))
WORKERS = int(os.getenv("FINETUNE_WORKERS", str(cfg.WORKERS)))
# Slightly higher LR + more epochs so domain scores push above 0.50
LR0 = float(os.getenv("FINETUNE_LR0", "0.002"))
RUN_NAME = os.getenv("FINETUNE_RUN_NAME", "ewaste_finetune_binary_conf50")


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


def resolve_device() -> str | int:
    require = os.getenv("TRAIN_REQUIRE_GPU", "1") == "1"
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        logger.info("Fine-tune on GPU 0: %s (%.1f GiB)", name, mem)
        return 0
    if require:
        raise SystemExit("CUDA required for fine-tune (TRAIN_REQUIRE_GPU=1).")
    logger.warning("CUDA unavailable — fine-tuning on CPU")
    return "cpu"


def find_best(run_dir: Path) -> Path:
    candidate = run_dir / "weights" / "best.pt"
    if candidate.is_file():
        return candidate
    matches = list(run_dir.rglob("best.pt"))
    if not matches:
        raise FileNotFoundError(f"best.pt not found under {run_dir}")
    return matches[0]


def backup_weights(path: Path) -> None:
    if not path.is_file():
        return
    backup = path.with_name("best_pre_binary_finetune.pt")
    shutil.copy2(path, backup)
    logger.info("Backed up current weights → %s", backup)


def main() -> None:
    setup_logging()

    if not FINETUNE_YAML.is_file():
        raise SystemExit(f"Missing {FINETUNE_YAML}. Run: python prepare_finetune.py")
    if not SOURCE_WEIGHTS.is_file():
        raise SystemExit(f"Missing start weights: {SOURCE_WEIGHTS}")

    device = resolve_device()
    cfg.PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Binary e-waste fine-tune from %s | epochs=%d batch=%d lr0=%s",
        SOURCE_WEIGHTS,
        EPOCHS,
        BATCH,
        LR0,
    )

    # Transfer learning from existing checkpoint; Ultralytics rebuilds Detect head for nc=1
    model = YOLO(str(SOURCE_WEIGHTS))
    results = model.train(
        data=str(FINETUNE_YAML),
        epochs=EPOCHS,
        batch=BATCH,
        imgsz=IMGSZ,
        workers=WORKERS,
        lr0=LR0,
        lrf=0.01,
        device=device,
        amp=device != "cpu",
        project=str(cfg.PROJECT_DIR),
        name=RUN_NAME,
        exist_ok=True,
        pretrained=False,
        optimizer="AdamW",
        patience=20,
        close_mosaic=10,
        verbose=True,
        # Emphasize classification so objectness/conf climbs on conveyor shots
        cls=1.0,
        box=7.5,
        hsv_h=0.01,
        hsv_s=0.5,
        hsv_v=0.4,
        degrees=8.0,
        translate=0.08,
        scale=0.4,
        fliplr=0.5,
        mosaic=0.8,
        mixup=0.05,
        copy_paste=0.1,
    )

    run_dir = Path(results.save_dir)
    logger.info("Fine-tune finished. Run dir: %s", run_dir)

    metrics = model.val(
        data=str(FINETUNE_YAML),
        imgsz=IMGSZ,
        batch=BATCH,
        device=device,
        workers=WORKERS,
    )
    map50 = float(getattr(metrics.box, "map50", 0.0) or 0.0)
    map50_95 = float(getattr(metrics.box, "map", 0.0) or 0.0)
    logger.info("Binary fine-tune val mAP50=%.4f  mAP50-95=%.4f", map50, map50_95)

    new_best = find_best(run_dir)
    backup_weights(cfg.BACKEND_MODEL_PATH)
    cfg.BACKEND_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(new_best, cfg.BACKEND_MODEL_PATH)
    logger.info("Updated production weights: %s", cfg.BACKEND_MODEL_PATH)


if __name__ == "__main__":
    main()
