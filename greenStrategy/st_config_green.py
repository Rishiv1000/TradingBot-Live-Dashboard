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

STRATEGY_NAME = "GREEN"
TARGET = 0.1
STOPLOSS = 0.1
LOOKBACK_DAYS = 0.05

GREEN_SYMBOLS_LIVE_TBL = "green_symbols_live"
GREEN_TRADES_LIVE_TBL = "green_trades_live"
