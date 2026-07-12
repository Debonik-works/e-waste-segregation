# USB serial guide

## Who talks to the Nano?

| Mode | Who opens COM port |
|------|--------------------|
| Local FastAPI with `SERIAL_ENABLED=true` | [`backend/serial_sender.py`](../backend/serial_sender.py) |
| Cloud Run (or serial disabled) | [`edge/serial_bridge.py`](../edge/serial_bridge.py) on a lab PC |

Only **one** process should open the port at a time.

## Windows

1. Plug Nano via USB
2. Device Manager → Ports (COM & LPT) → note `COMx`
3. Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:SERIAL_ENABLED="true"
$env:SERIAL_PORT="COM3"
uvicorn main:app --host 0.0.0.0 --port 8080
```

Or edge bridge:

```powershell
cd edge
.\setup_venv.ps1
.\.venv\Scripts\Activate.ps1
$env:SERIAL_PORT="COM3"
$env:API_URL="http://127.0.0.1:8080"
python serial_bridge.py
```

Leave `SERIAL_PORT` empty to auto-detect (Arduino/CH340 hints).

## Linux

```bash
ls /dev/ttyUSB* /dev/ttyACM*
sudo usermod -aG dialout $USER   # then re-login
export SERIAL_PORT=/dev/ttyUSB0
```

## Protocol

Host → Nano: `RIGHT\n` `LEFT\n` `STOP\n` `STATUS\n`  
Nano → Host: `OK` / `DONE` / `ERROR`

Retries: configurable (`SERIAL_RETRIES`, default 3).

## Conflict with Arduino IDE Serial Monitor

Close the Serial Monitor before starting Python — Windows locks the COM port to one application.
