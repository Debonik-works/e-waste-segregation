"""Logging helpers and small utilities."""

from __future__ import annotations

import logging
import time
from typing import Iterator

import colorlog


def setup_logging(level: int = logging.INFO) -> None:
    """Configure colored root logging once."""
    root = logging.getLogger()
    if any(isinstance(h, colorlog.StreamHandler) for h in root.handlers):
        root.setLevel(level)
        return

    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s %(levelname)-8s%(reset)s %(name)s — %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


class Timer:
    """Context manager measuring wall-clock seconds."""

    def __init__(self) -> None:
        self.start: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> Timer:
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed = time.perf_counter() - self.start


def chunks(data: bytes, size: int) -> Iterator[bytes]:
    """Yield fixed-size byte chunks."""
    for i in range(0, len(data), size):
        yield data[i : i + size]
