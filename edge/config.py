"""Configuration for the local serial bridge."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BridgeSettings(BaseSettings):
    """Settings for polling Cloud Run / local API and driving the Nano."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    api_url: str = Field(default="http://127.0.0.1:8080", alias="API_URL")
    poll_interval_s: float = Field(default=1.0, alias="POLL_INTERVAL_S")
    serial_port: str = Field(default="", alias="SERIAL_PORT")
    serial_baud: int = Field(default=9600, alias="SERIAL_BAUD")
    serial_timeout: float = Field(default=2.0, alias="SERIAL_TIMEOUT")
    serial_retries: int = Field(default=3, alias="SERIAL_RETRIES")
    motor_duration_ms: int = Field(default=1500, alias="MOTOR_DURATION_MS")
    motor_cooldown_ms: int = Field(default=0, alias="MOTOR_COOLDOWN_MS")


@lru_cache
def get_settings() -> BridgeSettings:
    """Cached bridge settings."""
    return BridgeSettings()
