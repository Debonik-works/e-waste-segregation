# Creates edge/.venv and installs requirements.txt
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not on PATH. Install Python 3.10+ and retry."
}

Write-Host "Creating virtual environment at edge/.venv ..."
python -m venv .venv

$pip = Join-Path $PSScriptRoot ".venv\Scripts\pip.exe"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

& $python -m pip install --upgrade pip
& $pip install -r requirements.txt

Write-Host ""
Write-Host "Done. Activate with:"
Write-Host "  .\edge\.venv\Scripts\Activate.ps1"
Write-Host "Then run:"
Write-Host "  python serial_bridge.py"
