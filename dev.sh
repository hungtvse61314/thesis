#!/usr/bin/env bash
# Run backend (FastAPI) and frontend (Vite) together for local development.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
  echo ""
  echo "Stopping..."
  jobs -p | xargs -r kill 2>/dev/null
}
trap cleanup EXIT INT TERM

echo "Starting backend on http://localhost:8000 ..."
(
  cd "$ROOT_DIR/backend"
  .venv/bin/python -m uvicorn app.main:app --reload --port 8000
) &

echo "Starting frontend on http://localhost:5173 ..."
(
  cd "$ROOT_DIR/frontend"
  npm run dev
) &

wait
