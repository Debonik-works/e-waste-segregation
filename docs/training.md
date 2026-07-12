# Local training guide

Training must run on your machine. Cloud Run never trains.

## 1. Create the training venv

```powershell
cd train
.\setup_venv.ps1
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
cd train
chmod +x setup_venv.sh
./setup_venv.sh
source .venv/bin/activate
```

## 2. Merge datasets

Sources:

- `dataset-2/` — YOLO labels (bbox + polygons → bbox)
- `ewaste/modified-dataset/` — class folders → full-image boxes
- `Identify-and-Segregate-E-Waste/ewaste/` — **skipped** (duplicate)

```powershell
python prepare_dataset.py
```

Outputs:

- `dataset/dataset.yaml`
- `dataset/train|valid|test/{images,labels}/`
- `dataset/classes.json`
- `backend/classes.json`

**38 classes** = 37 from dataset-2 + `Printer`.

## 3. Train YOLOv8n

```powershell
python train.py
```

Environment overrides:

| Variable | Default | Meaning |
|----------|---------|---------|
| `TRAIN_EPOCHS` | 50 | Epochs |
| `TRAIN_BATCH` | 16 | Batch size |
| `TRAIN_IMGSZ` | 640 | Image size |
| `TRAIN_WORKERS` | 4 | Dataloader workers |
| `TRAIN_LR0` | 0.01 | Initial LR |
| `TRAIN_EXPORT_ONNX` | 0 | Set `1` to export ONNX |
| `YOLO_WEIGHTS` | yolov8n.pt | Pretrained weights |

Example short smoke run:

```powershell
$env:TRAIN_EPOCHS="2"
$env:TRAIN_BATCH="8"
python train.py
```

GPU is used automatically when CUDA PyTorch is installed. `setup_venv.ps1` installs CUDA 12.4 wheels if `nvidia-smi` works.

```powershell
# Confirm GPU
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# Require GPU (exit if CUDA missing)
$env:TRAIN_REQUIRE_GPU="1"
python train.py

# Or pick device: auto | cpu | 0 | 0,1
$env:TRAIN_DEVICE="0"
```

Augmentation: [`train/augment.yaml`](../train/augment.yaml).

## 4. Export / publish weights

`train.py` always copies:

`train/runs/ewaste_yolov8n/weights/best.pt` → `backend/model/best.pt`

Optional ONNX:

```powershell
$env:TRAIN_EXPORT_ONNX="1"
python train.py
```

## 5. Verify

```powershell
Test-Path ..\backend\model\best.pt
```

Then start the backend (see root README).
