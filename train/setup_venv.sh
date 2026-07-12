#!/usr/bin/env bash
# Creates train/.venv and installs requirements with CUDA PyTorch when a GPU is present.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required (3.10+)." >&2
  exit 1
fi

echo "Creating virtual environment at train/.venv ..."
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  echo "NVIDIA GPU detected — installing PyTorch with CUDA 12.4 ..."
  ./.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
else
  echo "No NVIDIA GPU detected — installing CPU PyTorch from PyPI ..."
fi

./.venv/bin/pip install -r requirements.txt

./.venv/bin/python -c "import torch; print('torch', torch.__version__, '| cuda', torch.cuda.is_available(), '| device', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"

echo ""
echo "Done. Activate with:"
echo "  source train/.venv/bin/activate"
echo "Then run:"
echo "  python prepare_dataset.py"
echo "  python train.py"
echo "Force GPU-only:  TRAIN_REQUIRE_GPU=1 python train.py"
