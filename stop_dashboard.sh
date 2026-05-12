#!/bin/bash
# ─────────────────────────────────────────────────────────────
# stop_live_dashboard.sh  —  Stop backend + frontend
# Usage: bash stop_live_dashboard.sh
# ─────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$BASE_DIR/.live_pids"

echo "[*] Stopping Live Dashboard services..."

# ── Kill via saved PIDs ───────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    while IFS= read -r pid; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "    Killed PID $pid"
        else
            echo "    PID $pid already stopped"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
else
    echo "[!] No PID file found — using port-based kill"
fi

# ── Fallback: kill by port ────────────────────────────────────
fuser -k 8000/tcp 2>/dev/null && echo "[✓] Port 8000 cleared" || true
fuser -k 5173/tcp 2>/dev/null && echo "[✓] Port 5173 cleared" || true

echo "[✓] Done"
