#!/bin/bash
# Utility: Creates required dirs and files
# Sourced by run_dashboard.sh

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$BASE_DIR/others/logs"

[ ! -f "$BASE_DIR/configuration/.env" ] && cp "$BASE_DIR/configuration/.env.example" "$BASE_DIR/configuration/.env" && echo "[✓] configuration/.env created"
[ ! -f "$BASE_DIR/dashboard-ui/.env" ]  && cp "$BASE_DIR/dashboard-ui/.env.example"  "$BASE_DIR/dashboard-ui/.env"  && echo "[✓] dashboard-ui/.env created"

touch "$BASE_DIR/others/logs/api.log"
touch "$BASE_DIR/others/logs/vite.log"

echo "[✓] Dirs and log files ready"
