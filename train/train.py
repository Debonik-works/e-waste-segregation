"""
Train YOLOv8n on the merged dataset, evaluate, optionally export ONNX,
and copy best.pt into backend/model/.

Uses CUDA GPU when available (set TRAIN_DEVICE to override).
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import colorlog
import torch
import yaml
from ultralytics import YOLO

import config as cfg

logger = logging.getLogger("train")


def setup_logging() -> None:
    """Configure colored console logging."""
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


def resolve_device() -> str | int | list[int]:
    """
    Resolve training device.

    Env ``TRAIN_DEVICE``:
      - ``auto`` (default): first CUDA GPU if present, else CPU
      - ``cpu``: force CPU
      - ``0`` / ``1``: single GPU index
      - ``0,1``: multi-GPU

    Env ``TRAIN_REQUIRE_GPU=1``: exit if CUDA is unavailable.
    """
    require_gpu = os.getenv("TRAIN_REQUIRE_GPU", "0") == "1"
    requested = os.getenv("TRAIN_DEVICE", "auto").strip().lower()

    cuda_ok = torch.cuda.is_available()
    if cuda_ok:
        n = torch.cuda.device_count()
        logger.info(
            "CUDA available: %d GPU(s), torch=%s, cuda_runtime=%s",
            n,
            torch.__version__,
            torch.version.cuda,
        )
        for i in range(n):
            props = torch.cuda.get_device_properties(i)
            mem_gb = props.total_memory / (1024**3)
            logger.info("  GPU %d: %s (%.1f GiB)", i, props.name, mem_gb)
    else:
        logger.warning(
            "CUDA not available (torch=%s). Install a CUDA build of PyTorch in train/.venv — "
            "see train/requirements.txt. Falling back to CPU unless TRAIN_REQUIRE_GPU=1.",
            torch.__version__,
        )

    if requested == "cpu":
        if require_gpu:
            raise SystemExit("TRAIN_REQUIRE_GPU=1 but TRAIN_DEVICE=cpu")
        logger.info("Using CPU (TRAIN_DEVICE=cpu)")
        return "cpu"

    if requested == "auto":
        if cuda_ok:
            name = torch.cuda.get_device_name(0)
            logger.info("Using GPU 0: %s", name)
            return 0
        if require_gpu:
            raise SystemExit(
                "TRAIN_REQUIRE_GPU=1 but no CUDA GPU found. "
                "Reinstall torch with CUDA in train/.venv (see requirements.txt)."
            )
        logger.warning("Training on CPU (this will be slow)")
        return "cpu"

    # Explicit device list / index, e.g. "0" or "0,1"
    if "," in requested:
        indices = [int(x.strip()) for x in requested.split(",") if x.strip() != ""]
        if not cuda_ok:
            raise SystemExit(f"TRAIN_DEVICE={requested} requires CUDA")
        logger.info("Using GPUs: %s", indices)
        return indices

    try:
        index = int(requested)
    except ValueError as exc:
        raise SystemExit(
            f"Invalid TRAIN_DEVICE={requested!r}. Use auto, cpu, 0, or 0,1"
        ) from exc

    if not cuda_ok:
        raise SystemExit(f"TRAIN_DEVICE={index} requires CUDA")
    logger.info("Using GPU %d: %s", index, torch.cuda.get_device_name(index))
    return index


def load_augment_overrides() -> dict:
    """Load augmentation hyperparameters from augment.yaml."""
    path = Path(__file__).resolve().parent / "augment.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"augment.yaml must be a mapping, got {type(data)}")
    return data


def find_best_weights(run_dir: Path) -> Path:
    """Locate best.pt under an Ultralytics run directory."""
    candidate = run_dir / "weights" / "best.pt"
    if candidate.is_file():
        return candidate
    matches = list(run_dir.rglob("best.pt"))
    if not matches:
        raise FileNotFoundError(f"best.pt not found under {run_dir}")
    return matches[0]


def copy_best_to_backend(best_pt: Path) -> Path:
    """Copy trained weights to backend/model/best.pt."""
    dest = cfg.BACKEND_MODEL_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_pt, dest)
    logger.info("Copied %s → %s", best_pt, dest)
    return dest


def main() -> None:
    """Train, evaluate, export, and publish best.pt."""
    setup_logging()

    if not cfg.DATASET_YAML.is_file():
        raise SystemExit(
            f"Missing {cfg.DATASET_YAML}. Run prepare_dataset.py first "
            "(inside train/.venv)."
        )

    device = resolve_device()
    use_gpu = device != "cpu"
    aug = load_augment_overrides()
    cfg.PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    # Slightly larger default batch is fine on GPU; keep config value as source of truth
    batch = cfg.BATCH
    logger.info(
        "Starting training: epochs=%d batch=%d imgsz=%d workers=%d lr0=%s device=%s amp=%s weights=%s",
        cfg.EPOCHS,
        batch,
        cfg.IMGSZ,
        cfg.WORKERS,
        cfg.LR0,
        device,
        use_gpu,
        cfg.PRETRAINED_WEIGHTS,
    )

    model = YOLO(cfg.PRETRAINED_WEIGHTS)
    results = model.train(
        data=str(cfg.DATASET_YAML),
        epochs=cfg.EPOCHS,
        batch=batch,
        imgsz=cfg.IMGSZ,
        workers=cfg.WORKERS,
        lr0=cfg.LR0,
        device=device,
        amp=use_gpu,  # mixed precision on GPU
        project=str(cfg.PROJECT_DIR),
        name=cfg.RUN_NAME,
        exist_ok=True,
        pretrained=True,
        optimizer="auto",
        verbose=True,
        **aug,
    )

    run_dir = Path(results.save_dir)
    logger.info("Training finished. Run dir: %s", run_dir)

    logger.info("Evaluating on validation set...")
    metrics = model.val(
        data=str(cfg.DATASET_YAML),
        imgsz=cfg.IMGSZ,
        batch=batch,
        device=device,
        workers=cfg.WORKERS,
    )
    map50 = float(getattr(metrics.box, "map50", 0.0) or 0.0)
    map50_95 = float(getattr(metrics.box, "map", 0.0) or 0.0)
    logger.info("Val mAP50=%.4f  mAP50-95=%.4f", map50, map50_95)

    best_pt = find_best_weights(run_dir)
    copy_best_to_backend(best_pt)

    if cfg.EXPORT_ONNX:
        logger.info("Exporting ONNX...")
        export_model = YOLO(str(best_pt))
        export_path = export_model.export(format="onnx", imgsz=cfg.IMGSZ)
        logger.info("ONNX export: %s", export_path)

    logger.info("Done. Inference weights ready at %s", cfg.BACKEND_MODEL_PATH)


if __name__ == "__main__":
    main()
