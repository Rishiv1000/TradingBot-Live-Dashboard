import os
import sys

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(STRATEGY_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config.base_config import *

# --- [STRATEGY SPECIFIC CONFIG] ---
STRATEGY_NAME = "GREEN3"
TARGET        = 0.1
STOPLOSS      = 0.1
LOOKBACK_DAYS = 0.05  # ~3 days of 1-min candles

# --- [STRATEGY SPECIFIC TABLE NAMES] ---
GREEN3_SYMBOLS_LIVE_TBL = "green3_symbols_live"
GREEN3_TRADES_LIVE_TBL  = "green3_trades_live"
