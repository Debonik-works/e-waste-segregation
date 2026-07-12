#!/usr/bin/env bash
# Creates backend/.venv and installs requirements.txt
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required (3.10+)." >&2
  exit 1
fi

echo "Creating virtual environment at backend/.venv ..."
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

echo ""
echo "Done. Activate with:"
echo "  source backend/.venv/bin/activate"
echo "Then run:"
echo "  uvicorn main:app --host 0.0.0.0 --port 8080 --reload"
