#!/bin/bash
# ─────────────────────────────────────────────────────────────
# run_dashboard.sh  —  Super Stable (Auto-Restart) Mode [LIVE]
# Usage: bash run_dashboard.sh
# ─────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

mkdir -p logs

# Startup Cleanup
echo "[*] Cleaning up old Live sessions..."
rm -f .stop_backend
pkill -f "uvicorn api:app" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 1

# Start Backend Loop
start_backend() {
    while true; do
        echo "🚀 Starting Live Backend (Port: 8000)..."
        # Removing --reload for absolute stability
        uvicorn api:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1
        
        # Check if we should stop for real
        if [ -f ".stop_backend" ]; then
            echo "[✓] Manual Shutdown detected. Live Loop stopped."
            pkill -f "npm run dev" 2>/dev/null
            exit 0
        fi
        
        echo "❌ LIVE Backend CRASHED! Restarting in 2s..."
        sleep 2
    done
}

# Start Frontend Loop
start_frontend() {
    while true; do
        echo "🚀 Starting Live Frontend (Port: 5173)..."
        cd "$BASE_DIR/dashboard-ui"
        VITE_PORT=5173 VITE_API_TARGET="http://127.0.0.1:8000" npm run dev > ../logs/vite.log 2>&1
        echo "⚠️ Live Frontend CRASHED! Restarting in 2s..."
        cd "$BASE_DIR"
        sleep 2
    done
}

# Run both in background loops
start_backend &
start_frontend &

echo "------------------------------------------------"
echo "✅ SUPER STABLE Live Dashboard is RUNNING."
echo "🔄 Auto-restart ENABLED for max uptime."
echo "------------------------------------------------"

# Keep the main script alive
wait
