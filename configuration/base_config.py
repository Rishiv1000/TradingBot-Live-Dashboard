import os

# Path to this config directory
CONFIG_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)

# ── 1. OS Level Storage (AAPanel / Env) ───────────────────────────────────────
API_KEY              = os.getenv("KITE_API_KEY")
API_SECRET           = os.getenv("KITE_API_SECRET")
DB_HOST              = os.getenv("DB_HOST", "localhost")
DB_USER              = os.getenv("DB_USER", "root")
DB_PASSWORD          = os.getenv("DB_PASSWORD", "")
DB_NAME              = os.getenv("DB_NAME", "trading_bot_live")
REAL_TRADING_ENABLED = False

# ── 2. TXT File Storage (Dynamic Access Token) ────────────────────────────────
ACCESS_TOKEN_FILE = os.path.join(CONFIG_DIR, "access_token.txt")
if os.path.exists(ACCESS_TOKEN_FILE):
    with open(ACCESS_TOKEN_FILE, "r") as f:
        ACCESS_TOKEN = f.read().strip()
else:
    ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")

# ── 3. Normal Settings (Hardcoded) ────────────────────────────────────────────
DEFAULT_QTY   = 1
LIVE_EXCHANGE = "NSE"
BUY_SLIPPAGE  = 0.05
SELL_SLIPPAGE = 0.05
BOT_RUNNING   = True

LOGS_DIR       = os.path.join(PROJECT_ROOT, "others", "logs")
DASHBOARD_PORT = 5173
API_PORT       = 8000