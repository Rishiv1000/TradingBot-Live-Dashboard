#!/bin/bash
# Utility: Creates required dirs and files
# Sourced by run_dashboard.sh

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$BASE_DIR/others/logs"
touch "$BASE_DIR/others/logs/api.log"
touch "$BASE_DIR/others/logs/vite.log"

echo "[✓] Dirs and log files ready"
