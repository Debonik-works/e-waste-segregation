# Creates train/.venv and installs requirements with CUDA PyTorch when a GPU is present.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not on PATH. Install Python 3.10+ and retry."
}

Write-Host "Creating virtual environment at train/.venv ..."
python -m venv .venv

$pip = Join-Path $PSScriptRoot ".venv\Scripts\pip.exe"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

& $python -m pip install --upgrade pip

# Prefer CUDA wheels when an NVIDIA GPU is available
$hasGpu = $false
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    & nvidia-smi | Out-Null
    if ($LASTEXITCODE -eq 0) { $hasGpu = $true }
}

if ($hasGpu) {
    Write-Host "NVIDIA GPU detected — installing PyTorch with CUDA 12.4 ..."
    & $pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
} else {
    Write-Host "No NVIDIA GPU detected — installing CPU PyTorch from PyPI ..."
}

& $pip install -r requirements.txt

Write-Host ""
& $python -c "import torch; print('torch', torch.__version__, '| cuda', torch.cuda.is_available(), '| device', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"

Write-Host ""
Write-Host "Done. Activate with:"
Write-Host "  .\train\.venv\Scripts\Activate.ps1"
Write-Host "Then run:"
Write-Host "  python prepare_dataset.py"
Write-Host "  python train.py"
Write-Host "Force GPU-only:  `$env:TRAIN_REQUIRE_GPU='1'; python train.py"
