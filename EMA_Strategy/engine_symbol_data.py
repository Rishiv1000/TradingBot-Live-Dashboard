import os
import sys
import pandas as pd
import pandas_ta as ta
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.append(ROOT_DIR)

import st_config as config
from config.candle_data import fetch_symbol_candles, build_symbol_dataframe

RELOAD_SIGNAL_FILE = os.path.join(STRATEGY_DIR, ".reload_symbols")
_symbol_cache = []
_cache_loaded = False

def check_ema_entry_signal(df):
    if df is None or len(df) < 2:
        return False, None
    
    signal_row = df.iloc[-2]
    
    if signal_row.get("cross_down") == 1:
        ema9 = signal_row["EMA_9"]
        ema20 = signal_row["EMA_20"]
        trigger_price = signal_row["close"]
        
        try:
            short_gap = config.EMA_SHORT_GAP
        except AttributeError:
            short_gap = 0.5
            
        gap_pct = (ema20 - ema9) / ema9
        if gap_pct >= short_gap:
            return True, trigger_price
            
    return False, None

def check_ema_exit_signal(df, trade, live_price):
    target_price = trade.get('target_price', 0)
    if live_price <= target_price:
        return True, target_price, "TARGET_HIT"
    
    if df is not None and len(df) >= 2:
        signal_row = df.iloc[-2]
        if signal_row.get("cross_up") == 1:
            return True, signal_row["close"], "EMA_REVERSAL"
            
    return False, None, None

def build_ema_dataframe(kite, token, days=None):
    try:
        if days is None:
            days = config.EMA_LOOKBACK_DAYS
        tf = config.EMA_TIMEFRAME
        
        records = fetch_symbol_candles(kite, token, days=days, timeframe=tf)
        df = build_symbol_dataframe(records)
        
        if df.empty: return None
        
        df["EMA_9"] = ta.ema(df["close"], length=9)
        df["EMA_20"] = ta.ema(df["close"], length=20)
        df["cross_down"] = ta.cross(df["EMA_9"], df["EMA_20"], above=False)
        df["cross_up"] = ta.cross(df["EMA_9"], df["EMA_20"], above=True)
        
        return df
    except Exception as e:
        print(f"Error building EMA DF: {e}")
        return None

def fetch_runtime_symbols(kite):
    global _symbol_cache, _cache_loaded
    if os.path.exists(RELOAD_SIGNAL_FILE):
        _cache_loaded = False
        os.remove(RELOAD_SIGNAL_FILE)
        
    if not _cache_loaded:
        _symbol_cache = _load_symbols_from_db()
        _cache_loaded = True
    return _symbol_cache

def _load_symbols_from_db():
    import mysql.connector
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        table = config.EMA_SYMBOLS_LIVE_TBL
        cursor.execute(f"SELECT symbol, instrument_token as token, exchange FROM {table}")
        symbols = cursor.fetchall()
        conn.close()
        return symbols
    except Exception as e:
        print(f"Error loading symbols: {e}")
        return []
