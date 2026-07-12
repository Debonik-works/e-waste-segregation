"""
FastAPI entrypoint for AI-powered e-waste segregation inference.

Model loads once at startup. No training. No database — latest result in RAM.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from model_loader import load_model
from routes import router
from serial_sender import serial_sender
from utils import setup_logging

logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load model and optional serial connection at startup; clean up on shutdown."""
    setup_logging()
    settings = get_settings()
    logger.info("Starting e-waste inference API")
    logger.info("Confidence threshold=%.2f serial_enabled=%s", settings.confidence_threshold, settings.serial_enabled)

    try:
        load_model(settings)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        raise

    if settings.serial_enabled:
        serial_sender.connect()

    yield

    serial_sender.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AI Powered E-Waste Segregation API",
    description="YOLOv8n inference for e-waste detection. In-memory latest only.",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
