import os
import sys
import time
import threading
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
if STRATEGY_DIR not in sys.path: sys.path.insert(0, STRATEGY_DIR)
if ROOT_DIR not in sys.path: sys.path.insert(0, ROOT_DIR)

import st_config_ema
from engine_symbol_data import refresh_all_ema_data
from engine_entry import EMAEntryEngine
from engine_exit import EMAExitEngine

def main():
    print(f"[{st_config_ema.STRATEGY_NAME}] 🚀 EMA Live Trading System Starting...")
    kite = st_config_ema.get_kite_session()
    if not kite:
        print(f"[{st_config_ema.STRATEGY_NAME}] ❌ Kite login failed. Exiting.")
        return

    df_cache = {}

    entry_engine = EMAEntryEngine(kite, df_cache)
    entry_engine.start()

    # ExitEngine runs KiteTicker (blocking) — run in daemon thread
    exit_engine = EMAExitEngine(kite, df_cache)
    threading.Thread(target=exit_engine.start, daemon=True).start()

    print(f"[{st_config_ema.STRATEGY_NAME}] ✅ Entry & Exit engines started. Entering data loop...")

    while True:
        try:
            # Blocks until next candle, then refreshes cache
            refresh_all_ema_data(kite, df_cache)
        except Exception as e:
            print(f"[{st_config_ema.STRATEGY_NAME}] ❌ Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
