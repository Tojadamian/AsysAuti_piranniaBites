#!/usr/bin/env bash
# Be tolerant of missing vars to avoid '$!' unbound issues
set -eo pipefail

# Activate venv if present
if [ -d "asysauti/bin" ]; then
  source "asysauti/bin/activate"
fi

# Ensure Python deps
python3 -m pip install -r requirements.txt >/dev/null || true

# Export envs (use .env if present via Flask)
export FLASK_APP=app.py
export FLASK_ENV=development

# If port 5000 is busy, skip starting backend and rely on existing instance
PORT_BUSY=0
if command -v lsof >/dev/null 2>&1; then
  if lsof -i :5000 -sTCP:LISTEN -P -n >/dev/null 2>&1; then
    PORT_BUSY=1
  fi
fi

BACK_PID=""
if [[ "$PORT_BUSY" -eq 0 ]]; then
  # Start backend (prefer python -m flask to avoid PATH issues)
  (python3 -m flask run &)
  BACK_PID=${!}
  echo "Backend started (PID: ${BACK_PID}). Starting frontend..."
else
  echo "Port 5000 already in use. Will only start frontend and use existing backend."
fi

# Start frontend
cd frontend
npm install
npm run dev

# On exit, kill backend if PID is set
if [[ -n "${BACK_PID}" ]]; then
  trap 'kill ${BACK_PID} 2>/dev/null || true' EXIT
fi
