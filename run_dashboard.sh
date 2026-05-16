#!/bin/bash
# Start Dashboard: bash run_dashboard.sh
# NOTE: Run util.sh ONCE after cloning.

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

source "$BASE_DIR/util.sh"

pkill -f "uvicorn api:app" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
pkill -f "tail -f.*api.log" 2>/dev/null
rm -f .stop_backend
sleep 1

echo "[*] Installing frontend dependencies..."
cd "$BASE_DIR/dashboard-ui" && npm install && cd "$BASE_DIR"
echo "[✓] npm install done"

echo "[*] Starting Frontend..."
(cd "$BASE_DIR/dashboard-ui" && VITE_PORT=5173 VITE_API_TARGET="http://127.0.0.1:8000" npm run dev >> "$BASE_DIR/others/logs/vite.log" 2>&1) &

echo "[*] Activating Python venv..."
source "/www/server/pyporject_evn/pythonapps/bin/activate"
echo "[✓] venv activated"

echo "[*] Starting Backend..."
echo "[*] Live logs enabled. Showing api.log below:"

# Background tail to show logs live in terminal
tail -n 0 -f "$BASE_DIR/others/logs/api.log" &
TAIL_PID=$!

# Cleanup background tail on script exit
trap "kill $TAIL_PID 2>/dev/null; exit" INT TERM

while true; do
    uvicorn api:app --host 0.0.0.0 --port 8000 >> "$BASE_DIR/others/logs/api.log" 2>&1
    [ -f "$BASE_DIR/.stop_backend" ] && echo "Stopped." && kill $TAIL_PID 2>/dev/null && exit 0
    echo "⚠️ Backend crashed. Restarting in 3s..."
    sleep 3
done
