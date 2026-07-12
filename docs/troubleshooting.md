# Troubleshooting

## `Model weights not found` / backend won't start

Train first so `backend/model/best.pt` exists:

```powershell
cd train
.\.venv\Scripts\Activate.ps1
python prepare_dataset.py
python train.py
```

## `ModuleNotFoundError` / wrong packages

You installed into the system Python. Recreate the component venv:

```powershell
cd train   # or backend / edge
Remove-Item -Recurse -Force .venv
.\setup_venv.ps1
.\.venv\Scripts\Activate.ps1
```

## Dataset merge path errors

Ensure folders exist:

- `dataset-2/train/images`
- `ewaste/modified-dataset/train/...`

Run `prepare_dataset.py` from `train/` with `train/.venv` active.

## Dashboard shows no images

1. `GET http://127.0.0.1:8080/health` → `model_loaded: true`
2. POST a test image to `/predict`
3. Dashboard must reach the same host (`VITE_API_URL` or Vite proxy)

## ESP32 upload fails

- Confirm FastAPI reachable from phone/PC on same WiFi
- Check `SERVER_URL` includes `/predict`
- Power ESP32 from 5V ≥1A supply
- Watch Serial at 115200 for HTTP codes

## Arduino always `ERROR` or no reply

- Baud must be 9600
- Close Serial Monitor / other apps using the port
- Try explicit `SERIAL_PORT`
- Verify GND shared with L298N

## Motors don't move

- ENA/ENB jumpers removed and wired to PWM pins
- VMOT battery connected and charged
- Common GND between Nano and L298N
- Raise `MOTOR_SPEED` in the Nano sketch

## Cloud Run OOM / timeout

- Increase memory to 2–4Gi
- Set `--concurrency 1`
- Confirm image includes `model/best.pt` (Docker build fails otherwise)

## Confidence always `unknown`

Raise image quality / lighting, or lower `CONFIDENCE_THRESHOLD` (e.g. `0.35`) via env / `GET /config`.
