import importlib
import os
import sys
import threading
import time
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.insert(0, STRATEGY_DIR)
sys.path.insert(0, BASE_DIR)

from kiteconnect import KiteConnect

# Import terminal capture
try:
    from configuration.terminal_capture import start_strategy_capture, stop_strategy_capture
except ImportError:
    def start_strategy_capture(name): pass
    def stop_strategy_capture(name): pass

import st_config_green
from engine_entry import EntryEngine
from engine_exit import ExitEngine
from configuration.candle_data import get_smart_sleep_seconds


def smart_sleep_wait():
    tf = getattr(st_config_green, "TIMEFRAME", "minute")
    sec = get_smart_sleep_seconds(tf)
    print(f"😴 [GREEN] Sleeping {sec}s until next candle refresh.")
    time.sleep(sec)


def main():
    print("🚀 Starting GREEN Strategy Runner (LIVE)...")
    start_strategy_capture("GREEN")

    # ── SAFETY LOCK ──────────────────────────────────────────────────────────
    if not getattr(st_config_green, "REAL_TRADING_ENABLED", False):
        print("🔒 [GREEN] BLOCKED: REAL_TRADING_ENABLED = False in base_config.py")
        print("🔒 [GREEN] Set REAL_TRADING_ENABLED = True in configuration/base_config.py to unlock.")
        stop_strategy_capture("GREEN")
        return
    # ─────────────────────────────────────────────────────────────────────────

    try:
        kite = st_config_green.get_kite_session()
        if not kite:
            raise ConnectionError("No valid Kite session. Login from dashboard first.")

        exit_engine = ExitEngine(kite)
        threading.Thread(target=exit_engine.start_monitoring, daemon=True).start()

        df_cache = {}
        entry_engine = EntryEngine(kite, df_cache)

        while True:
            importlib.reload(st_config_green)
            entry_engine.run_cycle()
            smart_sleep_wait()
    finally:
        # Stop terminal capture
        stop_strategy_capture("GREEN")


if __name__ == "__main__":
    main()
