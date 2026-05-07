#!/bin/bash
# ─────────────────────────────────────────────────────────────
# run_live_dashboard.sh  —  Start backend + frontend
# Usage: bash run_live_dashboard.sh
# ─────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$BASE_DIR/.live_pids"

cd "$BASE_DIR"

# ── Activate virtualenv if present ───────────────────────────
for VENV in "$BASE_DIR/venv" "$BASE_DIR/.venv" "$BASE_DIR/../venv"; do
    if [ -f "$VENV/bin/activate" ]; then
        source "$VENV/bin/activate"
        echo "[✓] Virtualenv activated: $VENV"
        break
    fi
done

# ── Check uvicorn is available ────────────────────────────────
if ! command -v uvicorn &>/dev/null; then
    echo "[!] uvicorn not found. Run: pip install -r shared/setup_system/requirements.txt"
    exit 1
fi

# ── Start FastAPI backend ─────────────────────────────────────
echo "[*] Starting FastAPI backend on port 8000..."
nohup uvicorn api:app --host 0.0.0.0 --port 8000 --reload \
    > "$BASE_DIR/logs/api.log" 2>&1 &
UVICORN_PID=$!

# ── Start Vite frontend ───────────────────────────────────────
echo "[*] Starting Vite dashboard on port 5173..."
cd "$BASE_DIR/dashboard-ui"
nohup npm run dev \
    > "$BASE_DIR/logs/vite.log" 2>&1 &
VITE_PID=$!

# ── Save PIDs ─────────────────────────────────────────────────
echo "$UVICORN_PID" >  "$PID_FILE"
echo "$VITE_PID"    >> "$PID_FILE"

echo ""
echo "[✓] Both services started"
echo "    FastAPI PID : $UVICORN_PID  →  logs/api.log"
echo "    Vite    PID : $VITE_PID     →  logs/vite.log"
echo ""
echo "  To stop:  bash stop_live_dashboard.sh"
echo "  API logs: tail -f $BASE_DIR/logs/api.log"
echo "  UI  logs: tail -f $BASE_DIR/logs/vite.log"
echo ""
