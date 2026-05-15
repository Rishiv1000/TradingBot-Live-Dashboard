import os
import sys
import time
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.append(ROOT_DIR)

import st_config_ema
from engine_symbol_data import build_ema_dataframe, fetch_runtime_symbols
from configuration.candle_data import update_symbol_dataframe_cache
from engine_entry import EMAEntryEngine
from engine_exit import EMAExitEngine

def smart_sleep(interval_minutes=1):
    now = datetime.now()
    seconds_to_wait = (interval_minutes * 60) - (now.second + (now.minute % interval_minutes) * 60) - 3
    if seconds_to_wait > 0:
        print(f"[{st_config_ema.STRATEGY_NAME}] 😴 Sleeping for {seconds_to_wait}s...")
        time.sleep(seconds_to_wait)

def main():
    print(f"[{st_config_ema.STRATEGY_NAME}] 🚀 EMA Trading System Starting (LIVE)...")
    kite = st_config_ema.get_kite_session()
    if not kite:
        print(f"[{st_config_ema.STRATEGY_NAME}] ❌ Login failed.")
        return

    ema_df_cache = {}

    entry_engine = EMAEntryEngine(kite, ema_df_cache)
    entry_engine.start()
    
    exit_engine = EMAExitEngine(kite, ema_df_cache)
    exit_engine.start()
    
    try:
        interval = st_config_ema.EMA_INTERVAL_MINUTES
    except AttributeError:
        interval = 5

    while True:
        try:
            symbols = fetch_runtime_symbols(kite)
            for item in symbols:
                symbol = item['symbol']
                try:
                    df = build_ema_dataframe(kite, item['token'])
                    ema_df_cache[symbol] = df
                    update_symbol_dataframe_cache(ema_df_cache, STRATEGY_DIR)
                except Exception: pass

            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Cache Updated.")
            smart_sleep(interval)
        except Exception as e:
            print(f"❌ Main Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
