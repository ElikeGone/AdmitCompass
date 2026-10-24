#!/usr/bin/env bash
# AdmitCompass review build: mock AI, no API key, fresh temporary account database. Linux/macOS.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if [ ! -x .venv/bin/python ]; then
  echo "Creating virtual environment and installing requirements (first run only)..."
  "$PY" -m venv .venv
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -r requirements.txt
fi

# No model key: Ask AI uses the offline mock; live analyses are refused. An empty value also prevents any
# .env file (here or in the parent folder) from loading a key, because existing environment values win.
export PORTKEY_API_KEY=""
export AC_COPILOT_MODE=mock
# Fresh, throwaway account database for every start (deleted with the temp folder).
DB_DIR="$(mktemp -d -t admitcompass-XXXXXX)"
export AC_DB_PATH="$DB_DIR/accounts.sqlite3"
trap 'rm -rf "$DB_DIR"' EXIT

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
echo "AdmitCompass (review build: mock AI, no API key) -> http://$HOST:$PORT"
echo "Temporary account database: $AC_DB_PATH"
.venv/bin/python -m uvicorn backend.app.main:app --host "$HOST" --port "$PORT"
