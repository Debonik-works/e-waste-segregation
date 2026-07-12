# AI Powered E-Waste Segregation System

**ESP32-CAM → FastAPI (YOLOv8n) → dashboard animations → Arduino Nano + L298N conveyor**

```
ESP32-CAM  --POST /predict-->  FastAPI (PC or Cloud Run)
                                 ├── SSE /events --> React dashboard
                                 └── serial (PC only) --> Arduino --> L298N --> motors
```

Cloud Run has no USB — use [`edge/serial_bridge.py`](edge/serial_bridge.py) on the PC with the Nano when the API is in the cloud.

---

## Prerequisites

- Python 3.10+, Node.js 20+, Arduino IDE  
- NVIDIA GPU optional (CUDA PyTorch in `train/.venv`)  
- **Always use each folder’s `.venv`** — never system `pip`

| Folder | Setup |
|--------|--------|
| `train/` | `.\setup_venv.ps1` |
| `backend/` | `.\setup_venv.ps1` |
| `edge/` | `.\setup_venv.ps1` |

---

## Setup (short)

### A. One-time — data, train, flash

```powershell
# 1) Merge datasets
cd train
.\setup_venv.ps1
.\.venv\Scripts\Activate.ps1
python prepare_dataset.py

# 2) Train (GPU if CUDA installed) → backend/model/best.pt
$env:TRAIN_REQUIRE_GPU="1"
python train.py
```

Flash firmware (Arduino IDE):

- [`firmware/esp32_cam/esp32_cam.ino`](firmware/esp32_cam/esp32_cam.ino) — **no WiFi hardcoded**
- [`firmware/arduino_nano/arduino_nano.ino`](firmware/arduino_nano/arduino_nano.ino) — wire L298N per [docs/l298n-wiring.md](docs/l298n-wiring.md)

### B. Every session — run local stack

```powershell
# Terminal 1 — API (must bind 0.0.0.0 so ESP32 can reach it)
cd backend
.\.venv\Scripts\Activate.ps1
# Optional Nano on this PC:
# $env:SERIAL_ENABLED="true"; $env:SERIAL_PORT="COM3"
uvicorn main:app --host 0.0.0.0 --port 8080

# Terminal 2 — dashboard
cd dashboard
npm install
npm run dev
```

Open http://localhost:5173

### C. Phone hotspot + ESP32 (Device setup popup)

1. Turn on **phone hotspot**; note **SSID + password**.
2. Connect **PC** to that hotspot.
3. In dashboard → **Device / WiFi setup**:
   - **WiFi SSID / password** = hotspot name & pass  
   - **Backend URL** = click **Detect LAN IP** → e.g. `http://192.168.43.12:8080`  
     (**never** `127.0.0.1` — ESP32 cannot reach it)
4. Power ESP32 → SoftAP **EWaste-Setup** / pass **ewaste123**.
5. Connect PC to **EWaste-Setup** → **Push to ESP32**.
6. Reconnect PC to the **phone hotspot**.
7. ESP32 joins hotspot and POSTs to `{backend}/predict` every 5s; dashboard shows scan → YOLO → conveyor.

Manual LAN IP (if needed): `ipconfig` → Wi‑Fi adapter **IPv4** while on the hotspot.

### D. Motors (optional)

| Mode | Where |
|------|--------|
| Local API | `$env:SERIAL_ENABLED="true"` on backend |
| Cloud Run API | `cd edge` → `API_URL=https://…` → `python serial_bridge.py` |

---

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/predict` | image → `{ewaste, category, confidence}` + SSE |
| GET | `/events` | live `frame` → `processing` → `result` |
| GET | `/latest` | latest in-memory result |
| GET | `/health` | health |
| GET | `/lan-info` | suggested PC LAN URL for ESP32 |
| GET/POST | `/device-config` | WiFi + API URL from dashboard |

---

## Cloud Run

Train locally first (`best.pt` in `backend/model/`). Then see [docs/cloud-run.md](docs/cloud-run.md).

```powershell
docker compose up --build   # local Docker; needs best.pt
```

---

## Docs

| Topic | File |
|-------|------|
| Full runbook | [docs/run-overall.md](docs/run-overall.md) |
| Training | [docs/training.md](docs/training.md) |
| ESP32 | [docs/esp32-setup.md](docs/esp32-setup.md) |
| Cloud Run | [docs/cloud-run.md](docs/cloud-run.md) |
| Nano / L298N / USB | [docs/arduino-nano-wiring.md](docs/arduino-nano-wiring.md), [docs/l298n-wiring.md](docs/l298n-wiring.md), [docs/usb-serial.md](docs/usb-serial.md) |
| Troubleshooting | [docs/troubleshooting.md](docs/troubleshooting.md) |

## Constraints

- No database — latest inference in RAM only  
- Train on PC only; Cloud Run = inference only  
- Model: `backend/model/best.pt`
