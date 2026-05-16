import os
from dotenv import load_dotenv

# Path to this config directory
CONFIG_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)

# Load .env from config directory
env_path = os.path.join(CONFIG_DIR, ".env")
load_dotenv(env_path)

# --- [SYSTEM & AUTH] ---
API_KEY           = os.getenv("KITE_API_KEY")
API_SECRET        = os.getenv("KITE_API_SECRET")
ACCESS_TOKEN      = os.getenv("KITE_ACCESS_TOKEN")
LOGS_DIR          = os.path.join(PROJECT_ROOT, "others", "logs")

# Credential Validation
if not API_KEY:
    print("⚠️ WARNING: KITE_API_KEY is missing in .env")
if not API_SECRET:
    print("⚠️ WARNING: KITE_API_SECRET is missing in .env")
if not ACCESS_TOKEN:
    print("ℹ️ INFO: KITE_ACCESS_TOKEN is missing (Login required)")

# --- [DASHBOARD & API PORTS] ---
DASHBOARD_PORT = 5173
API_PORT       = 8000

# --- [DATABASE CONFIG] ---
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME     = os.getenv("DB_NAME", "trading_bot_live")

# --- [COMMON TRADING SETTINGS] ---
DEFAULT_QTY          = 1
LIVE_EXCHANGE        = "NSE"
BOT_RUNNING          = True
BUY_SLIPPAGE         = 0.5
SELL_SLIPPAGE        = 0.5