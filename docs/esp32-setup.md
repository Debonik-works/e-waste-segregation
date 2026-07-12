# ESP32-CAM setup

Firmware: [`firmware/esp32_cam/esp32_cam.ino`](../firmware/esp32_cam/esp32_cam.ino)

WiFi and backend URL are **not hardcoded**. You enter them in the dashboard **Device setup** modal.

## Hardware

- AI Thinker ESP32-CAM (OV2640)
- USB-TTL programmer (IO0 → GND for flash)
- 5V power supply (≥1A recommended)

## Arduino IDE

1. Install **ESP32** board support (Espressif)
2. Install library **ArduinoJson**
3. Board: **AI Thinker ESP32-CAM**
4. Upload speed: 115200
5. Flash [`esp32_cam.ino`](../firmware/esp32_cam/esp32_cam.ino) (no SSID in source)

## First-time provisioning (dashboard popup)

1. Start FastAPI + dashboard (`backend` + `dashboard`).
2. Power the ESP32. With no saved credentials it opens SoftAP:
   - SSID: **EWaste-Setup**
   - Password: **ewaste123**
   - IP: **192.168.4.1**
3. Open the dashboard → **Set up WiFi & API**.
4. Enter:
   - Your home/lab **WiFi SSID + password**
   - **Backend base URL** — local e.g. `http://192.168.1.10:8080` or Cloud Run `https://….run.app`
   - Capture interval (default 5000 ms)
5. **Save on backend** (stored in API RAM).
6. Connect **this PC** to WiFi **EWaste-Setup**.
7. Click **Push to ESP32** (POST `http://192.168.4.1/config`).
8. ESP32 saves to flash (NVS), reboots, joins your WiFi, and POSTs JPEGs to `{api_base_url}/predict`.
9. Reconnect your PC to the normal WiFi so the dashboard can talk to the backend again.

## Runtime flow

```text
ESP32 capture (every N ms)
    → POST multipart /predict  (local or Cloud Run)
    → Backend SSE: frame (scan) → processing → result
    → Dashboard laser scan → YOLO panel → conveyor LEFT/RIGHT
```

## SoftAP endpoints (setup mode only)

| Method | Path | Body |
|--------|------|------|
| GET | `/` | plain help text |
| GET | `/status` | JSON status |
| POST | `/config` | `{ssid, password, api_base_url, interval_ms}` |

## Tips

- Prefer 5V external power; USB-TTL alone is often unstable
- Backend URL must be reachable from the ESP32 (same LAN for local HTTP)
- Cloud Run needs HTTPS — extend the sketch with `WiFiClientSecure` if you deploy TLS-only
- To re-enter setup: erase NVS / flash again, or clear Preferences namespace `ewaste`
