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
ACCESS_TOKEN_FILE = os.path.join(CONFIG_DIR, "access_token.txt")

# --- [DATABASE CONFIG] ---
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME     = os.getenv("DB_NAME", "trading_bot_live")

# --- [COMMON TRADING SETTINGS] ---
DEFAULT_QTY          = 1
LIVE_EXCHANGE        = "NSE"
TIMEFRAME            = "minute"
BOT_RUNNING          = True
REAL_TRADING_ENABLED = True
