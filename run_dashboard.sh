#!/bin/bash
# ─────────────────────────────────────────────────────────────
# run_dashboard.sh  —  Optimized Start (Live Project)
# Usage: bash run_dashboard.sh
# ─────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

mkdir -p logs

echo "[*] Cleaning up Live sessions..."
pkill -f "uvicorn api:app" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 1

echo "[*] Reading configuration..."
DASHBOARD_PORT=$(python -c "import sys; sys.path.insert(0, '.'); from config.base_config import DASHBOARD_PORT; print(DASHBOARD_PORT)" 2>/dev/null)
API_PORT=$(python -c "import sys; sys.path.insert(0, '.'); from config.base_config import API_PORT; print(API_PORT)" 2>/dev/null)

[ -z "$DASHBOARD_PORT" ] && DASHBOARD_PORT=5173
[ -z "$API_PORT" ] && API_PORT=8000

echo "🚀 Starting Live Backend (Port: $API_PORT)..."
echo "⚠️  REAL TRADING MODE ACTIVE"
uvicorn api:app --host 0.0.0.0 --port $API_PORT --reload > logs/api.log 2>&1 &
UVICORN_PID=$!

sleep 2
if ! ps -p $UVICORN_PID > /dev/null; then
    echo "❌ ERROR: Live Backend failed to start!"
    echo "--- Last 10 lines of logs/api.log ---"
    tail -n 10 logs/api.log
    exit 1
fi
echo "[✓] Live Backend is UP (PID: $UVICORN_PID)"

echo "🚀 Starting Live Frontend (Port: $DASHBOARD_PORT)..."
cd "$BASE_DIR/dashboard-ui"
VITE_PORT=$DASHBOARD_PORT VITE_API_TARGET="http://127.0.0.1:$API_PORT" npm run dev > ../logs/vite.log 2>&1 &
VITE_PID=$!

sleep 2
if ! ps -p $VITE_PID > /dev/null; then
    echo "❌ ERROR: Live Frontend failed to start!"
    echo "--- Last 10 lines of logs/vite.log ---"
    tail -n 10 ../logs/vite.log
    kill $UVICORN_PID 2>/dev/null
    exit 1
fi
echo "[✓] Live Frontend is UP (PID: $VITE_PID)"

echo "------------------------------------------------"
echo "✅ LIVE Dashboard is ready: http://localhost:$DASHBOARD_PORT"
echo "------------------------------------------------"

wait $UVICORN_PID $VITE_PID
