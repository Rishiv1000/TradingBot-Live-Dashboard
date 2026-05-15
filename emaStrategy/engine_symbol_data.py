import os
import sys
import pandas as pd
import pandas_ta as ta
import pickle
import time
from datetime import datetime
from zoneinfo import ZoneInfo

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
if STRATEGY_DIR not in sys.path: sys.path.insert(0, STRATEGY_DIR)
if ROOT_DIR not in sys.path: sys.path.insert(0, ROOT_DIR)

import st_config_ema
from api_shared import db_fetchall
from configuration.candle_data import fetch_symbol_candles, build_symbol_dataframe, interval_minutes

def get_ema_smart_sleep(buffer_sec=3):
    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    interval = interval_minutes(st_config_ema.EMA_TIMEFRAME)
    minutes_now = now.hour * 60 + now.minute
    remaining = (interval * 60) - ((minutes_now % interval) * 60 + now.second)
    if remaining <= 0: return interval * 60
    return remaining + buffer_sec

def build_ema_dataframe(kite, token, days=None):
    try:
        if days is None:
            days = st_config_ema.EMA_LOOKBACK_DAYS
        tf = st_config_ema.EMA_TIMEFRAME
        records = fetch_symbol_candles(kite, token, days=days, timeframe=tf)
        df = build_symbol_dataframe(records)
        if df.empty: return None
        df["EMA_9"] = ta.ema(df["close"], length=9)
        df["EMA_20"] = ta.ema(df["close"], length=20)
        df["cross_down"] = ta.cross(df["EMA_9"], df["EMA_20"], above=False)
        df["cross_up"] = ta.cross(df["EMA_9"], df["EMA_20"], above=True)

        # Cap to MAX_CANDLES — flush older rows to prevent memory bloat
        max_candles = getattr(st_config_ema, "MAX_CANDLES", 500)
        if len(df) > max_candles:
            df = df.tail(max_candles).reset_index(drop=True)

        return df
    except Exception as e:
        print(f"Error building EMA DF for token {token}: {e}")
        return None


def refresh_all_ema_data(kite, df_cache):
    sec = get_ema_smart_sleep()
    # print(f"[{st_config_ema.STRATEGY_NAME}] 😴 Waiting {sec}s for next candle...")
    time.sleep(sec)

    table = st_config_ema.EMA_SYMBOLS_LIVE_TBL
    symbols = db_fetchall(f"SELECT instrument_token FROM {table}")

    new_cache = {}
    for row in symbols:
        token = row['instrument_token']
        if not token: continue
        df = build_ema_dataframe(kite, token)
        if df is not None:
            new_cache[token] = df

    df_cache.clear()
    df_cache.update(new_cache)

    try:
        cache_file = os.path.join(STRATEGY_DIR, "live_df_cache.pkl")
        with open(cache_file, "wb") as f:
            pickle.dump(df_cache, f)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 [EMA-LIVE] Data Refreshed & PKL Saved.")
    except Exception as e:
        print(f"⚠️ [EMA-LIVE] Cache save error: {e}")
