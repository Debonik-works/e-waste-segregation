"""Run YOLOv8 inference and push live scan/result events to the dashboard."""

from __future__ import annotations

import base64
import logging
import time
import uuid
from typing import Any

import cv2
import numpy as np

from config import Settings, get_settings
from events import live_bus
from model_loader import predict_raw
from serial_sender import serial_sender
from state import LatestInference, state
from utils import Timer

logger = logging.getLogger("predict")


def decode_image(data: bytes) -> np.ndarray:
    """Decode image bytes to BGR ndarray."""
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode image bytes")
    return image


def encode_jpeg(image: np.ndarray, quality: int = 85) -> bytes:
    """Encode BGR image to JPEG bytes."""
    ok, buf = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("JPEG encode failed")
    return buf.tobytes()


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def extract_detections(result: Any, id_to_slug: dict[int, str]) -> list[dict[str, Any]]:
    """Convert Ultralytics boxes to JSON-friendly detections."""
    detections: list[dict[str, Any]] = []
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return detections

    xyxy = boxes.xyxy.cpu().numpy()
    confs = boxes.conf.cpu().numpy()
    clss = boxes.cls.cpu().numpy().astype(int)

    for i in range(len(boxes)):
        class_id = int(clss[i])
        slug = id_to_slug.get(class_id, f"class-{class_id}")
        x1, y1, x2, y2 = [float(v) for v in xyxy[i]]
        detections.append(
            {
                "class_id": class_id,
                "category": slug,
                "confidence": float(confs[i]),
                "bbox": [x1, y1, x2, y2],
            }
        )
    detections.sort(key=lambda d: d["confidence"], reverse=True)
    return detections


def decide(
    detections: list[dict[str, Any]],
    threshold: float,
    allowed: list[str],
) -> tuple[bool, str, float]:
    """
    Pick best detection and apply confidence threshold.

    Any accepted detection means e-waste (conveyor RIGHT). Category is the
    detected slug (``ewaste`` for the single-class fine-tuned model).
    """
    if not detections:
        return False, "unknown", 0.0

    best = detections[0]
    conf = float(best["confidence"])
    category = str(best["category"]) or "ewaste"

    if conf < threshold:
        return False, "unknown", conf

    if allowed and category not in allowed and category != "ewaste":
        return False, "unknown", conf

    return True, category, conf


def annotate(image: np.ndarray, detections: list[dict[str, Any]], threshold: float) -> np.ndarray:
    """Draw bounding boxes on a copy of the image."""
    canvas = image.copy()
    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
        conf = det["confidence"]
        color = (0, 220, 120) if conf >= threshold else (80, 80, 200)
        label = f"{det['category']} {conf:.2f}"
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            canvas,
            label,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
    return canvas


def run_prediction(image_bytes: bytes, settings: Settings | None = None) -> dict[str, Any]:
    """
    Pipeline with live dashboard push:

    1. Decode image → publish ``frame`` (scan animation + original image)
    2. Run YOLO → publish ``processing``
    3. Decide / annotate / serial → publish ``result`` (conveyor diversion)
    """
    settings = settings or get_settings()
    request_id = uuid.uuid4().hex
    state.increment_requests()

    image = decode_image(image_bytes)
    original_jpeg = encode_jpeg(image)
    id_to_slug = settings.class_id_to_slug()

    # Phase 1 — push raw frame so dashboard can start laser-scan animation
    scanning = LatestInference(
        request_id=request_id,
        timestamp=time.time(),
        phase="scan",
        original_jpeg=original_jpeg,
    )
    state.set_latest(scanning)
    live_bus.publish(
        {
            "type": "frame",
            "request_id": request_id,
            "phase": "scan",
            "original_image_b64": _b64(original_jpeg),
            "timestamp": scanning.timestamp,
        }
    )

    # Phase 2 — inference
    live_bus.publish(
        {
            "type": "processing",
            "request_id": request_id,
            "phase": "process",
        }
    )
    state.patch_latest(phase="process")

    with Timer() as timer:
        result = predict_raw(
            image,
            imgsz=settings.inference_imgsz,
            conf=min(0.1, settings.confidence_threshold),
        )
    inference_ms = timer.elapsed * 1000.0

    detections = extract_detections(result, id_to_slug)
    single_ewaste, single_category, single_confidence = decide(
        detections,
        threshold=settings.confidence_threshold,
        allowed=settings.allowed_class_list(),
    )

    # Accumulate frames in AppState
    frame_index, final_decision, accumulated = state.add_frame_prediction({
        "ewaste": single_ewaste,
        "category": single_category,
        "confidence": single_confidence,
        "detections": detections,
    })

    # Keep showing the current annotated frame in real-time
    annotated = annotate(image, detections, settings.confidence_threshold)
    annotated_jpeg = encode_jpeg(annotated)

    # Send serial command only on the 5th frame (final decision)
    serial_command: str | None = None
    serial_status: str | None = None
    if final_decision:
        final_ewaste = accumulated["ewaste"]
        if settings.serial_enabled:
            serial_command, serial_status = serial_sender.send_for_prediction(final_ewaste)
        ewaste = final_ewaste
        category = accumulated["category"]
        confidence = accumulated["confidence"]
        detections = accumulated["detections"]
    else:
        # Intermediate frames (1-4): do not trigger conveyor diversion
        ewaste = False
        category = single_category
        confidence = single_confidence

    latest = LatestInference(
        request_id=request_id,
        timestamp=time.time(),
        phase="result",
        ewaste=ewaste,
        category=category,
        confidence=round(confidence, 4),
        inference_ms=round(inference_ms, 2),
        serial_command=serial_command,
        serial_status=serial_status,
        original_jpeg=original_jpeg,
        annotated_jpeg=annotated_jpeg,
        detections=detections,
        frame_index=frame_index,
        final_decision=final_decision,
    )
    state.set_latest(latest)

    live_bus.publish(
        {
            "type": "result",
            "request_id": request_id,
            "phase": "result",
            "ewaste": ewaste,
            "category": category,
            "confidence": round(confidence, 4),
            "inference_ms": round(inference_ms, 2),
            "serial_command": serial_command,
            "serial_status": serial_status,
            "detections": detections,
            "original_image_b64": _b64(original_jpeg),
            "annotated_image_b64": _b64(annotated_jpeg),
            "timestamp": latest.timestamp,
            "frame_index": frame_index,
            "final_decision": final_decision,
        }
    )

    if frame_index > 0:
        if final_decision:
            verdict_str = "♻️  E-WASTE DETECTED" if ewaste else "❌ REJECT / NOT E-WASTE"
            logger.info(
                "\n"
                "============================================================\n"
                "   [VERDICT] %s\n"
                "   Category: %s (Confidence: %.2f)\n"
                "   Action: Sent %s command to motor (Status: %s)\n"
                "============================================================\n",
                verdict_str,
                category.upper(),
                confidence,
                serial_command,
                serial_status,
            )
        else:
            logger.info(
                "Frame %d/5: category=%s conf=%.3f ewaste=%s",
                frame_index,
                single_category,
                single_confidence,
                single_ewaste,
            )
    else:
        logger.info(
            "System cooling down (no scan): category=%s conf=%.3f",
            single_category,
            single_confidence,
        )

    return {
        "ewaste": ewaste,
        "category": category,
        "confidence": round(confidence, 4),
        "request_id": request_id,
        "inference_ms": round(inference_ms, 2),
        "serial_command": serial_command,
        "serial_status": serial_status,
        "detections": detections,
    }
