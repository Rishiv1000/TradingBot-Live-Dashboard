import os
import sys
import time

import mysql.connector

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

import st_config as config
from config.candle_data import (
    build_symbol_dataframe,
    fetch_symbol_candles,
    update_symbol_dataframe_cache,
)

# ── In-memory symbol cache ────────────────────────────────────────────────────
# Loaded once at startup, refreshed when RELOAD_SIGNAL_FILE exists
RELOAD_SIGNAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".reload_symbols")
_symbol_cache = []
_cache_loaded = False


def _load_symbols_from_db():
    global _symbol_cache, _cache_loaded
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )
    cursor = conn.cursor(dictionary=True)
    symbols_table = getattr(config, "SYMBOLS_TABLE", "symbols_green")
    limit = getattr(config, "MAX_SYMBOLS_PER_CYCLE", 50)
    cursor.execute(
        f"SELECT symbol, instrument_token AS token, exchange FROM {symbols_table} LIMIT %s",
        (limit,),
    )
    _symbol_cache = cursor.fetchall()
    conn.close()
    _cache_loaded = True
    print(f"[GREEN] Symbol cache loaded: {[s['symbol'] for s in _symbol_cache]}")
    return _symbol_cache


def fetch_runtime_symbols(kite):
    global _cache_loaded
    # Check if dashboard requested a reload
    if os.path.exists(RELOAD_SIGNAL_FILE):
        try:
            os.remove(RELOAD_SIGNAL_FILE)
        except Exception:
            pass
        _cache_loaded = False
        print("[GREEN] Symbol cache reload triggered.")

    if not _cache_loaded:
        _load_symbols_from_db()

    return _symbol_cache


def build_green_dataframe(kite, token):
    records = fetch_symbol_candles(
        kite,
        token,
        days=getattr(config, "LOOKBACK_DAYS", 3.0),
        timeframe=getattr(config, "TIMEFRAME", "minute"),
    )
    df = build_symbol_dataframe(records)
    return df 
