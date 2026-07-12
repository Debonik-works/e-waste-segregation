# Creates backend/.venv and installs requirements.txt
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not on PATH. Install Python 3.10+ and retry."
}

Write-Host "Creating virtual environment at backend/.venv ..."
python -m venv .venv

$pip = Join-Path $PSScriptRoot ".venv\Scripts\pip.exe"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

& $python -m pip install --upgrade pip
& $pip install -r requirements.txt

Write-Host ""
Write-Host "Done. Activate with:"
Write-Host "  .\backend\.venv\Scripts\Activate.ps1"
Write-Host "Then run:"
Write-Host "  uvicorn main:app --host 0.0.0.0 --port 8080 --reload"
