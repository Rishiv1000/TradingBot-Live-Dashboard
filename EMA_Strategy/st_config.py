import os
import sys

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(STRATEGY_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from config.base_config import *
except ImportError:
    sys.path.append(PROJECT_ROOT)
    from config.base_config import *

# --- [STRATEGY SPECIFIC CONFIG] ---
STRATEGY_NAME = 'EMA'
TARGET = 0.5
STOPLOSS = 0.5
EMA_LOOKBACK_DAYS = 3.0
EMA_TIMEFRAME = '5minute'

# --- [STRATEGY SPECIFIC TABLE NAMES] ---
EMA_SYMBOLS_LIVE_TBL     = "ema_symbols_live"     
EMA_TRADES_LIVE_TBL      = "ema_trades_live"
