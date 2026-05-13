import os
import sys
import time
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.append(ROOT_DIR)

import st_config as config
from config.base_config import get_kite_session
from engine_symbol_data import build_ema_dataframe, fetch_runtime_symbols
from config.candle_data import update_symbol_dataframe_cache

def smart_sleep(interval_minutes=1):
    now = datetime.now()
    seconds_to_wait = (interval_minutes * 60) - (now.second + (now.minute % interval_minutes) * 60) - 3
    if seconds_to_wait > 0:
        print(f"[{config.STRATEGY_NAME}] 😴 Sleeping for {seconds_to_wait}s until next candle...")
        time.sleep(seconds_to_wait)

def main():
    print(f"[{config.STRATEGY_NAME}] 📈 Scanner Only Mode Started (LIVE).")
    kite = get_kite_session()
    
    df_cache = {}
    
    tf = getattr(config, "EMA_TIMEFRAME", "minute")
    interval = 5 if "5" in tf else 1

    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [{config.STRATEGY_NAME}] 🔍 Scanning symbols for Chart (LIVE)...")
            symbols = fetch_runtime_symbols(kite)
            
            for item in symbols:
                symbol = item['symbol']
                try:
                    # Fetch data and calculate EMA/Signals
                    df = build_ema_dataframe(kite, item['token'])
                    
                    # Update local cache and save for Dashboard
                    df_cache[symbol] = df
                    update_symbol_dataframe_cache(df_cache, STRATEGY_DIR)
                    
                    print(f"[{config.STRATEGY_NAME}] Updated: {symbol}")
                    time.sleep(0.35)
                except Exception as e:
                    print(f"[{config.STRATEGY_NAME}] ❌ Error for {symbol}: {e}")

            print(f"[{config.STRATEGY_NAME}] ✅ All symbols updated.")
            smart_sleep(interval)
        except Exception as e:
            print(f"[{config.STRATEGY_NAME}] ❌ Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
