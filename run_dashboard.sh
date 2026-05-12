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
    echo "[!] uvicorn not found. Run: pip install -r config/requirements.txt"
    exit 1
fi

# ── Get server IP ─────────────────────────────────────────────
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$SERVER_IP" ] && SERVER_IP="localhost"

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

# ── Wait a moment for services to bind ───────────────────────
sleep 2

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║        📈 Live Trading Dashboard — Started           ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
printf "║  🌐 Dashboard  :  http://%-27s║\n" "$SERVER_IP:5173  "
printf "║  ⚙️  API        :  http://%-27s║\n" "$SERVER_IP:8000  "
echo "║                                                      ║"
echo "║  ⚠️  WARNING: REAL TRADING IS ACTIVE                 ║"
echo "║                                                      ║"
echo "╠══════════════════════════════════════════════════════╣"
printf "║  FastAPI PID  :  %-35s║\n" "$UVICORN_PID"
printf "║  Vite    PID  :  %-35s║\n" "$VITE_PID"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  Stop  :  bash stop_live_dashboard.sh                ║"
echo "║  Logs  :  tail -f logs/api.log                       ║"
echo "║           tail -f logs/vite.log                      ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
