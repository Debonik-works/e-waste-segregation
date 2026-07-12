"""
Local edge bridge: poll GET /latest from FastAPI (Cloud Run or local)
and send RIGHT/LEFT to the Arduino Nano over USB serial.

Cloud Run cannot open a COM port — run this on the lab PC that has the Nano attached.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import colorlog
import httpx

from config import get_settings

logger = logging.getLogger("serial_bridge")

try:
    import serial
    from serial.tools import list_ports
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pyserial is required. Activate edge/.venv and install requirements.") from exc


def setup_logging() -> None:
    """Colored console logging."""
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s %(levelname)-8s%(reset)s %(message)s",
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
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def detect_port(configured: str) -> str:
    """Return configured port or auto-detect Arduino-like device."""
    if configured.strip():
        return configured.strip()
    ports = list(list_ports.comports())
    hints = ("arduino", "ch340", "usb serial", "usb-serial", "wch", "silicon labs")
    for port in ports:
        desc = f"{port.description} {port.manufacturer or ''}".lower()
        if any(h in desc for h in hints):
            logger.info("Auto-detected %s (%s)", port.device, port.description)
            return port.device
    if ports:
        logger.info("Using first port %s", ports[0].device)
        return ports[0].device
    raise RuntimeError("No serial ports found. Plug in the Arduino Nano or set SERIAL_PORT.")


class ArduinoClient:
    """Minimal serial client with retry."""

    def __init__(self, port: str, baud: int, timeout: float, retries: int) -> None:
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.retries = retries
        self._conn: Optional[serial.Serial] = None

    def connect(self) -> None:
        """Open serial and wait for Nano reset."""
        self._conn = serial.Serial(self.port, self.baud, timeout=self.timeout, write_timeout=self.timeout)
        time.sleep(2.0)
        logger.info("Connected to Arduino on %s @ %d", self.port, self.baud)

    def close(self) -> None:
        """Close port."""
        if self._conn and self._conn.is_open:
            self._conn.close()
        self._conn = None

    def send(self, command: str) -> str:
        """Send command; return OK/DONE/ERROR."""
        command = command.strip().upper()
        for attempt in range(1, self.retries + 1):
            try:
                if self._conn is None or not self._conn.is_open:
                    self.connect()
                assert self._conn is not None
                self._conn.reset_input_buffer()
                self._conn.write(f"{command}\n".encode("ascii"))
                self._conn.flush()
                logger.info("TX [%d/%d] %s", attempt, self.retries, command)
                deadline = time.time() + self.timeout
                while time.time() < deadline:
                    line = self._conn.readline().decode("ascii", errors="ignore").strip().upper()
                    if line in {"OK", "DONE", "ERROR"}:
                        logger.info("RX %s", line)
                        return line
                logger.warning("Timeout waiting for %s", command)
            except Exception as exc:  # noqa: BLE001
                logger.error("Serial error: %s", exc)
                self.close()
                time.sleep(0.2)
        return "ERROR"


def main() -> None:
    """Poll /latest and drive motors for each new request_id."""
    setup_logging()
    settings = get_settings()
    port = detect_port(settings.serial_port)
    arduino = ArduinoClient(port, settings.serial_baud, settings.serial_timeout, settings.serial_retries)
    arduino.connect()

    last_id: str | None = None
    cooldown_s = max(settings.motor_duration_ms, settings.motor_cooldown_ms) / 1000.0
    latest_url = settings.api_url.rstrip("/") + "/latest"
    logger.info("Polling %s every %.1fs", latest_url, settings.poll_interval_s)

    try:
        with httpx.Client(timeout=10.0) as client:
            while True:
                try:
                    resp = client.get(latest_url)
                    resp.raise_for_status()
                    payload = resp.json()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Poll failed: %s", exc)
                    time.sleep(settings.poll_interval_s)
                    continue

                if not payload.get("available"):
                    time.sleep(settings.poll_interval_s)
                    continue

                request_id = payload.get("request_id")
                if not request_id or request_id == last_id:
                    time.sleep(settings.poll_interval_s)
                    continue

                ewaste = bool(payload.get("ewaste"))
                command = "RIGHT" if ewaste else "LEFT"
                logger.info(
                    "New inference %s category=%s conf=%s → %s",
                    str(request_id)[:8],
                    payload.get("category"),
                    payload.get("confidence"),
                    command,
                )
                status = arduino.send(command)
                if status == "ERROR":
                    logger.error("Arduino returned ERROR for %s", command)
                last_id = request_id
                time.sleep(cooldown_s)
    except KeyboardInterrupt:
        logger.info("Interrupted — shutting down")
    finally:
        arduino.close()


if __name__ == "__main__":
    main()
