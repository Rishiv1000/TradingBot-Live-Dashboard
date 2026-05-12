#!/bin/bash
# ─────────────────────────────────────────────────────────────
# setup.sh  —  Run once after cloning to configure everything
# Usage: bash setup.sh
# ─────────────────────────────────────────────────────────────
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   TradingBot Live — Setup Script         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Create shared/.env from example ───────────────────────
if [ ! -f "shared/.env" ]; then
    cp shared/.env.example shared/.env
    echo "[✓] Created shared/.env from example"
    echo ""
    echo "  ┌─ IMPORTANT ──────────────────────────────────────┐"
    echo "  │  Edit shared/.env and fill in your credentials:  │"
    echo "  │    - KITE_API_KEY                                 │"
    echo "  │    - KITE_API_SECRET                              │"
    echo "  │    - DB_PASSWORD                                  │"
    echo "  └───────────────────────────────────────────────────┘"
    echo ""
else
    echo "[✓] shared/.env already exists — skipping"
fi

# ── 2. Create dashboard-ui/.env from example ─────────────────
if [ ! -f "dashboard-ui/.env" ]; then
    cp dashboard-ui/.env.example dashboard-ui/.env
    echo "[✓] Created dashboard-ui/.env from example"
else
    echo "[✓] dashboard-ui/.env already exists — skipping"
fi

# ── 3. Create access_token.txt if missing ────────────────────
if [ ! -f "shared/access_token.txt" ]; then
    touch shared/access_token.txt
    echo "[✓] Created empty shared/access_token.txt"
fi

# ── 4. Create logs directory ─────────────────────────────────
mkdir -p logs
echo "[✓] logs/ directory ready"

# ── 5. Install Python dependencies ───────────────────────────
echo ""
echo "[*] Installing Python dependencies..."
pip install -r shared/setup_system/requirements.txt
echo "[✓] Python dependencies installed"

# ── 6. Install Node dependencies ─────────────────────────────
echo ""
echo "[*] Installing Node dependencies..."
cd dashboard-ui
npm install
cd "$BASE_DIR"
echo "[✓] Node dependencies installed"

# ── 7. Done ──────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Setup complete!                        ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  Next steps:"
echo "  1. Edit shared/.env  →  add your DB password & Kite keys"
echo "  2. Start services    →  bash run_live_dashboard.sh"
echo "  3. Setup database    →  click 'Setup DB' in the dashboard"
echo ""
echo "  ⚠️  WARNING: This is LIVE trading. Real money at risk!"
echo ""
