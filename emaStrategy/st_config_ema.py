import os
import sys

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(STRATEGY_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from configuration.base_config import *

def get_kite_session():
    from kiteconnect import KiteConnect

    if not API_KEY or not os.path.exists(ACCESS_TOKEN_FILE):
        return None
    kite = KiteConnect(api_key=API_KEY, timeout=30)
    with open(ACCESS_TOKEN_FILE, "r") as f:
        token = f.read().strip()
    if not token:
        return None
    kite.set_access_token(token)
    try:
        kite.profile()
        return kite
    except Exception:
        return None

STRATEGY_NAME = "EMA"
TARGET = 0.5
STOPLOSS = 0.5
EMA_LOOKBACK_DAYS = 3.0
EMA_TIMEFRAME = "5minute"
EMA_INTERVAL_MINUTES = 5
EMA_SHORT_GAP = 0.5
DEFAULT_QTY = 1

EMA_SYMBOLS_LIVE_TBL = "ema_symbols_live"
EMA_TRADES_LIVE_TBL = "ema_trades_live"
