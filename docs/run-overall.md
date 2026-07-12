# Full ecosystem: where to run what

Two machines matter: **your PC** (always) and optionally **Google Cloud**. The ESP32 and Arduino are hardware.

```text
ESP32-CAM ──POST /predict──► FastAPI (PC or Cloud Run)
                                │
                                ├── SSE /events ──► Dashboard (browser on PC)
                                │
                                └── (if Cloud Run) GET /latest ◄── serial_bridge.py (PC)
                                                      │
Arduino Nano ◄── USB Serial RIGHT/LEFT ───────────────┘
       │
     L298N → two motors → RIGHT e-waste / LEFT reject
```

---

## One-time (already mostly done)

| Step | Where | What |
|------|--------|------|
| 1. Merge dataset | **PC** → `train/.venv` | `python prepare_dataset.py` |
| 2. Train model | **PC** → `train/.venv` + GPU | `python train.py` → writes `backend/model/best.pt` |
| 3. Flash ESP32 | **PC** + Arduino IDE | `firmware/esp32_cam/esp32_cam.ino` (no WiFi in code) |
| 4. Flash Nano | **PC** + Arduino IDE | `firmware/arduino_nano/arduino_nano.ino` |
| 5. Wire motors | Bench | Nano ↔ L298N ↔ 2 motors ([docs/l298n-wiring.md](docs/l298n-wiring.md)) |

---

## Everyday run — Option A: everything local (best first test)

Use this when ESP32, PC, and Nano are on the **same lab network / USB**.

| # | Run on | Command / action | Role |
|---|--------|------------------|------|
| 1 | **PC** | `cd backend` → activate `.venv` → `uvicorn main:app --host 0.0.0.0 --port 8080` | Inference + SSE + optional serial |
| 2 | **PC** | `cd dashboard` → `npm run dev` → open http://localhost:5173 | Live UI / animations |
| 3 | **PC** (browser) | Device setup: WiFi + `http://YOUR_PC_LAN_IP:8080` → join SoftAP **EWaste-Setup** → **Push to ESP32** | Provision camera |
| 4 | **ESP32** | Powered on, joins WiFi, every 5s POSTs to `/predict` | Capture + upload |
| 5 | **PC** (same backend) | Optional: `$env:SERIAL_ENABLED="true"` before uvicorn *or* leave serial off and use bridge below | Drive Nano |
| 6 | **Arduino Nano** | USB to PC | Motors from `RIGHT`/`LEFT` |

**Serial (pick one, not both):**
- Backend: `SERIAL_ENABLED=true` + `SERIAL_PORT=COMx`, **or**
- Separate: `cd edge` → `.venv` → `API_URL=http://127.0.0.1:8080` → `python serial_bridge.py`

**Dashboard URL for ESP32 backend field:** `http://192.168.x.x:8080` (PC’s LAN IP, not `127.0.0.1` — ESP32 can’t see localhost).

---

## Everyday run — Option B: Cloud Run inference (plan production path)

Use when the API is in the cloud; **motors still need the PC** (Cloud Run has no USB).

| # | Run on | What | Role |
|---|--------|------|------|
| 1 | **GCP** | `gcloud builds submit ./backend` + `gcloud run deploy …` ([docs/cloud-run.md](docs/cloud-run.md)) | Host FastAPI + `best.pt` (`SERIAL_ENABLED=false`) |
| 2 | **PC** | `cd dashboard` → `$env:VITE_API_URL="https://YOUR-SERVICE.run.app"` → `npm run dev` | UI against cloud |
| 3 | **PC** (browser) | Device setup: home WiFi + Cloud Run base URL → SoftAP push | ESP32 targets cloud `/predict` |
| 4 | **ESP32** | Uploads to Cloud Run | Capture |
| 5 | **PC** | `cd edge` → `API_URL=https://YOUR-SERVICE.run.app` → `python serial_bridge.py` | Poll `/latest` → USB Nano |
| 6 | **Arduino Nano** | USB to **that same PC** | Conveyor |

---

## What talks to what (checklist)

| Component | Runs where | Talks to |
|-----------|------------|----------|
| `train.py` | PC only | Disk → `backend/model/best.pt` |
| FastAPI | PC **or** Cloud Run | ESP32 (`/predict`), dashboard (`/events`, `/latest`) |
| Dashboard | Browser on PC | FastAPI URL (local or Cloud Run) |
| ESP32 | Hardware | WiFi → FastAPI `/predict` |
| `serial_bridge.py` | PC with Nano | FastAPI `/latest` + COM port |
| Backend serial | Only if API is on PC | COM port directly |
| Arduino + L298N | Hardware | USB from PC |

---

## Minimal “fully working” sequence (local)

1. USB Nano plugged into PC; L298N powered.  
2. Start **backend** (port 8080).  
3. Start **dashboard**.  
4. Provision **ESP32** via Device setup (LAN IP of PC).  
5. Enable serial (backend flag **or** edge bridge).  
6. Place item under camera → every ~5s: upload → scan animation → YOLO → conveyor LEFT/RIGHT.

Training stays on the PC forever; Cloud Run never trains — only serves `best.pt`.
backeend run command: uvicorn main:app --host 0.0.0.0 --port 8080
venv command: .venv/Scripts/activate
Because **Push to ESP32** does not talk to your FastAPI URL. It talks to the **camera’s temporary Wi‑Fi network**.

### Two different networks

| Moment | What Wi‑Fi the PC must be on | Who you talk to |
|--------|------------------------------|-----------------|
| Normal use | Phone hotspot | FastAPI at `http://YOUR_PC_IP:8080` |
| **Push to ESP32** | SoftAP **EWaste-Setup** | ESP32 at `http://192.168.4.1/config` |

When the ESP32 has no saved Wi‑Fi, it becomes its own router:

- SSID: `EWaste-Setup`
- Password: `ewaste123`
- Its address on that network: **always** `192.168.4.1`

Your phone hotspot and `EWaste-Setup` are **different** networks. A PC on the hotspot cannot reach `192.168.4.1`, so the browser shows **Failed to fetch**.

### What the button actually does

```text
1. POST http://localhost:8080/device-config     ← your backend (works on hotspot)
2. POST http://192.168.4.1/config               ← ESP32 SoftAP (only if PC joined EWaste-Setup)
```

Step 2 fails if you’re still on the phone hotspot.

### Correct sequence

1. Fill form (hotspot SSID/password + Detect LAN IP URL) while on hotspot — **Save on backend** is fine here.  
2. Switch PC Wi‑Fi to **EWaste-Setup**.  
3. Click **Push to ESP32** (now `192.168.4.1` works).  
4. ESP32 saves credentials, reboots, joins the phone hotspot.  
5. Switch PC back to the phone hotspot so the dashboard can see FastAPI again.

So: the error isn’t “wrong API path” — it’s “PC isn’t on the ESP32’s setup Wi‑Fi.”