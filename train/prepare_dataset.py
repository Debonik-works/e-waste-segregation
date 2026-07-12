"""
Merge dataset-2 (YOLO) and ewaste (folder classification) into a single YOLO dataset.

- Converts polygon labels in dataset-2 to axis-aligned bounding boxes.
- Converts ewaste class-folder images into full-image YOLO boxes.
- Skips Identify-and-Segregate-E-Waste/ewaste (duplicate of ewaste/).
- Writes dataset/dataset.yaml and dataset/classes.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from pathlib import Path

import colorlog

import config as cfg

logger = logging.getLogger("prepare_dataset")


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


def long_path(path: Path) -> str:
    """Return a Windows extended-length path when needed."""
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def short_stem(prefix: str, original: str) -> str:
    """
    Build a short unique stem to avoid Windows MAX_PATH issues with long Roboflow names.
    """
    digest = hashlib.sha1(original.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def polygon_to_bbox(coords: list[float]) -> tuple[float, float, float, float]:
    """
    Convert flat normalized polygon [x1,y1,x2,y2,...] to YOLO cx,cy,w,h.

    Values are clamped to [0, 1]. Degenerate polygons fall back to a tiny box.
    """
    if len(coords) < 4 or len(coords) % 2 != 0:
        raise ValueError(f"Invalid polygon coordinate count: {len(coords)}")

    xs = coords[0::2]
    ys = coords[1::2]
    x_min = max(0.0, min(xs))
    x_max = min(1.0, max(xs))
    y_min = max(0.0, min(ys))
    y_max = min(1.0, max(ys))

    w = max(x_max - x_min, 1e-6)
    h = max(y_max - y_min, 1e-6)
    cx = min(1.0, max(0.0, (x_min + x_max) / 2.0))
    cy = min(1.0, max(0.0, (y_min + y_max) / 2.0))
    return cx, cy, w, h


def convert_label_line(line: str) -> str | None:
    """
    Normalize one YOLO label line to detection format: class cx cy w h.

    Returns None for empty/comment lines.
    """
    text = line.strip()
    if not text or text.startswith("#"):
        return None

    parts = text.split()
    if len(parts) < 5:
        logger.warning("Skipping malformed label line: %s", text[:80])
        return None

    class_id = int(float(parts[0]))
    nums = [float(x) for x in parts[1:]]

    if len(nums) == 4:
        cx, cy, w, h = nums
    else:
        cx, cy, w, h = polygon_to_bbox(nums)

    return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def ensure_split_dirs(split: str) -> tuple[Path, Path]:
    """Create and return (images_dir, labels_dir) for a split."""
    images = cfg.MERGED_DATASET_DIR / split / "images"
    labels = cfg.MERGED_DATASET_DIR / split / "labels"
    images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)
    return images, labels


def unique_stem(dest_images: Path, preferred: str) -> str:
    """Return a unique filename stem under dest_images (preferred already short)."""
    stem = preferred
    idx = 0
    while any(dest_images.glob(f"{stem}.*")):
        idx += 1
        stem = f"{preferred}_{idx}"
    return stem


def copy_image(src: Path, dest_images: Path, stem: str) -> Path:
    """Copy image to dest_images using stem and original suffix."""
    dest = dest_images / f"{stem}{src.suffix.lower()}"
    shutil.copyfile(long_path(src), long_path(dest))
    return dest


def merge_dataset2() -> dict[str, int]:
    """Copy and convert dataset-2 into the merged dataset. Returns per-split counts."""
    counts = {"train": 0, "valid": 0, "test": 0}
    split_map = {"train": "train", "valid": "valid", "test": "test"}

    for src_split, dest_split in split_map.items():
        src_images = cfg.DATASET2_DIR / src_split / "images"
        src_labels = cfg.DATASET2_DIR / src_split / "labels"
        if not src_images.is_dir():
            logger.warning("Missing dataset-2 images: %s", src_images)
            continue

        dest_images, dest_labels = ensure_split_dirs(dest_split)
        image_files = sorted(
            p for p in src_images.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        )

        for img_path in image_files:
            label_path = src_labels / f"{img_path.stem}.txt"
            stem = unique_stem(dest_images, short_stem(f"d2{dest_split[0]}", img_path.name))
            try:
                copy_image(img_path, dest_images, stem)
            except OSError as exc:
                logger.error("Failed to copy %s: %s", img_path.name[:60], exc)
                continue

            out_label = dest_labels / f"{stem}.txt"
            if label_path.is_file():
                converted: list[str] = []
                try:
                    raw = Path(long_path(label_path)).read_text(encoding="utf-8", errors="ignore")
                except OSError as exc:
                    logger.error("Failed to read label for %s: %s", img_path.name[:60], exc)
                    out_label.write_text("", encoding="utf-8")
                    counts[dest_split] += 1
                    continue
                for line in raw.splitlines():
                    try:
                        norm = convert_label_line(line)
                    except ValueError as exc:
                        logger.warning("%s: %s", label_path.name[:40], exc)
                        continue
                    if norm:
                        converted.append(norm)
                out_label.write_text("\n".join(converted) + ("\n" if converted else ""), encoding="utf-8")
            else:
                out_label.write_text("", encoding="utf-8")
                logger.warning("No label for %s", img_path.name[:60])

            counts[dest_split] += 1

        logger.info("dataset-2 %s → %s images", src_split, counts[dest_split])

    return counts


def merge_ewaste(name_ids: dict[str, int]) -> dict[str, int]:
    """Convert ewaste classification folders into YOLO full-image boxes."""
    counts = {"train": 0, "valid": 0, "test": 0}

    if not cfg.EWASTE_DIR.is_dir():
        logger.error("ewaste dataset missing: %s", cfg.EWASTE_DIR)
        return counts

    for src_split, dest_split in cfg.EWASTE_SPLIT_MAP.items():
        split_root = cfg.EWASTE_DIR / src_split
        if not split_root.is_dir():
            logger.warning("Missing ewaste split: %s", split_root)
            continue

        dest_images, dest_labels = ensure_split_dirs(dest_split)

        for class_dir in sorted(p for p in split_root.iterdir() if p.is_dir()):
            folder_name = class_dir.name
            canonical = cfg.EWASTE_FOLDER_TO_NAME.get(folder_name)
            if canonical is None:
                logger.warning("Unknown ewaste folder %s — skipping", folder_name)
                continue
            class_id = name_ids[canonical]

            images = sorted(
                p for p in class_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            )
            for img_path in images:
                stem = unique_stem(
                    dest_images,
                    short_stem(f"ew{dest_split[0]}{class_id}", f"{canonical}_{img_path.name}"),
                )
                try:
                    copy_image(img_path, dest_images, stem)
                except OSError as exc:
                    logger.error("Failed to copy ewaste %s: %s", img_path.name, exc)
                    continue
                label_line = f"{class_id} 0.500000 0.500000 1.000000 1.000000\n"
                (dest_labels / f"{stem}.txt").write_text(label_line, encoding="utf-8")
                counts[dest_split] += 1

        logger.info("ewaste %s → %s images", src_split, counts[dest_split])

    return counts


def write_dataset_yaml(names: list[str]) -> None:
    """Write Ultralytics dataset.yaml with absolute dataset root path."""
    root = cfg.MERGED_DATASET_DIR.resolve().as_posix()
    lines = [
        "# Auto-generated by train/prepare_dataset.py — do not edit by hand",
        f"path: {root}",
        "train: train/images",
        "val: valid/images",
        "test: test/images",
        "",
        f"nc: {len(names)}",
        "names:",
    ]
    for idx, name in enumerate(names):
        lines.append(f"  {idx}: {name}")
    lines.append("")
    cfg.DATASET_YAML.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote %s", cfg.DATASET_YAML)


def write_classes_json(names: list[str]) -> None:
    """Write id/name/slug mapping for the backend and dashboard."""
    payload = {
        "nc": len(names),
        "classes": [
            {"id": idx, "name": name, "slug": cfg.to_slug(name), "ewaste": True}
            for idx, name in enumerate(names)
        ],
        "future_reject_classes": ["plastic", "metal", "glass"],
    }
    text = json.dumps(payload, indent=2) + "\n"
    cfg.CLASSES_JSON.write_text(text, encoding="utf-8")
    # Also bake into backend/ so Docker image has class metadata without mounting dataset/
    backend_classes = cfg.ROOT / "backend" / "classes.json"
    backend_classes.write_text(text, encoding="utf-8")
    logger.info("Wrote %s and %s", cfg.CLASSES_JSON, backend_classes)


def reset_merged_dataset() -> None:
    """Remove previous merged train/valid/test trees (keep root)."""
    if cfg.MERGED_DATASET_DIR.exists():
        for split in ("train", "valid", "test"):
            split_path = cfg.MERGED_DATASET_DIR / split
            if split_path.exists():
                shutil.rmtree(split_path)
    cfg.MERGED_DATASET_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Entry point: merge sources into dataset/."""
    setup_logging()
    logger.info("Merging datasets into %s", cfg.MERGED_DATASET_DIR)

    if not cfg.DATASET2_DIR.is_dir():
        raise SystemExit(f"dataset-2 not found at {cfg.DATASET2_DIR}")

    names = cfg.class_names()
    name_ids = cfg.name_to_id()
    assert len(names) == 38, f"Expected 38 classes, got {len(names)}"

    reset_merged_dataset()
    d2_counts = merge_dataset2()
    ew_counts = merge_ewaste(name_ids)

    write_dataset_yaml(names)
    write_classes_json(names)

    total = {k: d2_counts.get(k, 0) + ew_counts.get(k, 0) for k in ("train", "valid", "test")}
    logger.info(
        "Merge complete — train=%d valid=%d test=%d (nc=%d)",
        total["train"],
        total["valid"],
        total["test"],
        len(names),
    )
    logger.info("Skipped Identify-and-Segregate-E-Waste/ewaste (duplicate of ewaste/).")


if __name__ == "__main__":
    main()
