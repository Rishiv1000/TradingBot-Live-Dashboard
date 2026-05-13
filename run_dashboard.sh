#!/bin/bash
# ─────────────────────────────────────────────────────────────
# run_dashboard.sh  —  Start Live Dashboard (No Auto-Stop)
# Usage: bash run_dashboard.sh
# ─────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

# Check deps
if ! command -v uvicorn &>/dev/null; then
    echo "[!] uvicorn not found."
    exit 1
fi

DASHBOARD_PORT=$(python -c "import sys; sys.path.insert(0, '.'); from config.base_config import DASHBOARD_PORT; print(DASHBOARD_PORT)")
API_PORT=$(python -c "import sys; sys.path.insert(0, '.'); from config.base_config import API_PORT; print(API_PORT)")

[ -z "$DASHBOARD_PORT" ] && DASHBOARD_PORT=5173
[ -z "$API_PORT" ] && API_PORT=8000

echo "🚀 Starting Live Trading Dashboard..."
echo "⚠️  WARNING: REAL TRADING MODE"

uvicorn api:app --host 0.0.0.0 --port $API_PORT --reload > logs/api.log 2>&1 &
UVICORN_PID=$!

cd "$BASE_DIR/dashboard-ui"
VITE_PORT=$DASHBOARD_PORT VITE_API_TARGET="http://127.0.0.1:$API_PORT" npm run dev > ../logs/vite.log 2>&1 &
VITE_PID=$!

echo "[✓] Live Dashboard is RUNNING. PIDs: API($UVICORN_PID), UI($VITE_PID)"
echo "[!] Auto-stop is DISABLED."

# Stay alive
wait $UVICORN_PID $VITE_PID
