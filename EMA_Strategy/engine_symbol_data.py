import mysql.connector
import os
import sys

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.append(STRATEGY_DIR)
sys.path.append(ROOT_DIR)

import st_config as config
from config.candle_data import (
    build_symbol_dataframe,
    fetch_symbol_candles,
    update_symbol_dataframe_cache,
)

# ── In-memory symbol cache ────────────────────────────────────────────────────
RELOAD_SIGNAL_FILE = os.path.join(STRATEGY_DIR, ".reload_symbols")
_symbol_cache = []
_cache_loaded = False


def _load_symbols_from_db():
    global _symbol_cache, _cache_loaded
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )
    cursor = conn.cursor(dictionary=True)
    
    table_name = getattr(config, "SYMBOLS_TABLE")
    cursor.execute(f"SELECT symbol, instrument_token as token, exchange FROM {table_name}")
    
    _symbol_cache = cursor.fetchall()
    conn.close()
    _cache_loaded = True
    print(f"[{config.STRATEGY_NAME}] Symbol cache loaded: {[s['symbol'] for s in _symbol_cache]}")
    return _symbol_cache


def fetch_runtime_symbols(kite):
    global _cache_loaded
    if os.path.exists(RELOAD_SIGNAL_FILE):
        try:
            os.remove(RELOAD_SIGNAL_FILE)
        except Exception:
            pass
        _cache_loaded = False
        print(f"[{config.STRATEGY_NAME}] Symbol cache reload triggered.")
    if not _cache_loaded:
        _load_symbols_from_db()
    return _symbol_cache


import pandas_ta as ta

def build_ema_dataframe(kite, token):
    records = fetch_symbol_candles(
        kite,
        token,
        days=getattr(config, 'EMA_LOOKBACK_DAYS'),
        timeframe=getattr(config, 'EMA_TIMEFRAME')
    )
    df = build_symbol_dataframe(records)
    
    # EMA Calculation using pandas_ta
    if not df.empty:
        df["EMA_9"] = ta.ema(df["close"], length=9)
        df["EMA_20"] = ta.ema(df["close"], length=20)
        
        # Crossup (9 over 20) and Crossdown (9 under 20)
        df["cross_up"] = ta.cross(df["EMA_9"], df["EMA_20"], above=True)
        df["cross_down"] = ta.cross(df["EMA_9"], df["EMA_20"], above=False)
        
    return df
