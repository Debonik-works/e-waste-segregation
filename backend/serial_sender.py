"""USB serial communication with the Arduino Nano (local deployments only)."""

from __future__ import annotations

import logging
import time
from typing import Optional

from config import Settings, get_settings

logger = logging.getLogger("serial_sender")

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover
    serial = None  # type: ignore
    list_ports = None  # type: ignore


class SerialSender:
    """
    Send RIGHT / LEFT / STOP / STATUS commands to the Arduino Nano.

    When SERIAL_ENABLED is false (Cloud Run), all methods are no-ops.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._conn: Optional[object] = None

    @property
    def enabled(self) -> bool:
        """Whether serial output is active."""
        return bool(self.settings.serial_enabled)

    def detect_port(self) -> str | None:
        """Auto-detect a likely Arduino COM/tty port."""
        if list_ports is None:
            return None
        ports = list(list_ports.comports())
        preferred_hints = ("arduino", "ch340", "usb serial", "usb-serial", "wch", "silicon labs")
        for port in ports:
            desc = f"{port.description} {port.manufacturer or ''}".lower()
            if any(h in desc for h in preferred_hints):
                logger.info("Auto-detected serial port %s (%s)", port.device, port.description)
                return port.device
        if ports:
            logger.info("Using first available serial port %s", ports[0].device)
            return ports[0].device
        return None

    def connect(self) -> bool:
        """Open the serial connection if enabled."""
        if not self.enabled:
            logger.info("Serial disabled (SERIAL_ENABLED=false)")
            return False
        if serial is None:
            logger.error("pyserial is not installed")
            return False

        port = self.settings.serial_port.strip() or self.detect_port()
        if not port:
            logger.error("No serial port configured or detected")
            return False

        try:
            self._conn = serial.Serial(
                port=port,
                baudrate=self.settings.serial_baud,
                timeout=self.settings.serial_timeout,
                write_timeout=self.settings.serial_timeout,
            )
            time.sleep(3.0)  # Nano resets on open
            logger.info("Serial connected on %s @ %d", port, self.settings.serial_baud)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Serial connect failed: %s", exc)
            self._conn = None
            return False

    def close(self) -> None:
        """Close the serial port."""
        if self._conn is not None:
            try:
                self._conn.close()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
            self._conn = None

    def send_command(self, command: str) -> str:
        """
        Send a command with retries. Returns Arduino reply or ERROR string.

        Valid commands: RIGHT, LEFT, STOP, STATUS.
        """
        command = command.strip().upper()
        if command not in {"RIGHT", "LEFT", "STOP", "STATUS"}:
            return "ERROR"

        if not self.enabled:
            logger.debug("Serial no-op command=%s", command)
            return "OK"

        if self._conn is None and not self.connect():
            return "ERROR"

        retries = max(1, self.settings.serial_retries)
        for attempt in range(1, retries + 1):
            try:
                assert self._conn is not None
                self._conn.reset_input_buffer()  # type: ignore[attr-defined]
                payload = f"{command}\n".encode("ascii")
                self._conn.write(payload)  # type: ignore[attr-defined]
                self._conn.flush()  # type: ignore[attr-defined]
                logger.info("Serial TX [%d/%d]: %s", attempt, retries, command)

                deadline = time.time() + self.settings.serial_timeout
                chunks: list[str] = []
                while time.time() < deadline:
                    line = self._conn.readline()  # type: ignore[attr-defined]
                    if not line:
                        continue
                    text = line.decode("ascii", errors="ignore").strip().upper()
                    if not text:
                        continue
                    chunks.append(text)
                    logger.info("Serial RX: %s", text)
                    if text in {"OK", "DONE", "ERROR"}:
                        return text
                logger.warning("Serial timeout waiting for reply to %s", command)
            except Exception as exc:  # noqa: BLE001
                logger.error("Serial send failed (attempt %d): %s", attempt, exc)
                self.close()
                self.connect()
            time.sleep(0.1)

        return "ERROR"

    def send_for_prediction(self, ewaste: bool) -> tuple[str, str]:
        """
        Map prediction to motor command.

        ewaste=True → RIGHT (e-waste bin), else LEFT (reject bin).
        """
        command = "RIGHT" if ewaste else "LEFT"
        status = self.send_command(command)
        return command, status


# Module-level sender used by routes
serial_sender = SerialSender()
