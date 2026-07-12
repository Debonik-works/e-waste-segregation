# Cloud Run deployment

Inference-only. Set `SERIAL_ENABLED=false` (default in the Dockerfile). Drive motors with `edge/serial_bridge.py` on a lab PC.

## Prerequisites

1. `python train/prepare_dataset.py` (in `train/.venv`)
2. `python train/train.py` so `backend/model/best.pt` exists
3. Google Cloud project with Cloud Run + Artifact Registry (or Container Registry) APIs enabled
4. `gcloud` CLI authenticated

## Build and deploy

From the repository root:

```powershell
$PROJECT_ID = "your-gcp-project"
$REGION = "us-central1"
$SERVICE = "ewaste-segregation"

gcloud config set project $PROJECT_ID

# Build from backend/ context (includes best.pt + classes.json)
gcloud builds submit ./backend --tag "gcr.io/$PROJECT_ID/$SERVICE"

gcloud run deploy $SERVICE `
  --image "gcr.io/$PROJECT_ID/$SERVICE" `
  --region $REGION `
  --platform managed `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --concurrency 1 `
  --max-instances 3 `
  --set-env-vars "SERIAL_ENABLED=false,CONFIDENCE_THRESHOLD=0.50,CORS_ORIGINS=*"
```

Notes:

- YOLO + PyTorch need **≥2Gi memory**; raise to 4Gi if OOM.
- `--concurrency 1` keeps one request per instance for predictable latency.
- Cloud Run injects `PORT`; the container listens on `8080` by default (matches Dockerfile). If Cloud Run sets another port, update the CMD or use:

```powershell
--set-env-vars "PORT=8080"
```

Or change Dockerfile CMD to use `$PORT`.

## Point ESP32 at Cloud Run

Set in `firmware/esp32_cam/esp32_cam.ino`:

```cpp
const char* SERVER_URL = "https://YOUR-SERVICE-XXXX.a.run.app/predict";
```

ESP32 must use HTTPS for Cloud Run public URLs (WiFiClientSecure) if you enable TLS-only — for simplest lab tests, use a local FastAPI IP over HTTP on the LAN.

For HTTPS uploads, extend the sketch with `WiFiClientSecure` and `http.begin(client, SERVER_URL)`.

## Edge serial bridge

```powershell
cd edge
.\setup_venv.ps1
.\.venv\Scripts\Activate.ps1
$env:API_URL="https://YOUR-SERVICE-XXXX.a.run.app"
python serial_bridge.py
```

## Local Docker smoke test

```powershell
cd backend
docker build -t ewaste-api .
docker run --rm -p 8080:8080 ewaste-api
curl http://127.0.0.1:8080/health
```

## Dashboard against Cloud Run

```powershell
cd dashboard
$env:VITE_API_URL="https://YOUR-SERVICE-XXXX.a.run.app"
npm run dev
```

Ensure Cloud Run `CORS_ORIGINS` includes your dashboard origin (or `*`).
