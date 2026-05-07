import os
import pickle
import sys
import time
from datetime import datetime

import mysql.connector
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

import config
from engine_symbol_data import build_green_dataframe, fetch_runtime_symbols, update_symbol_dataframe_cache
from shared.candle_data import interval_minutes
from shared.order_manager import place_real_buy


BOT_START_TIME = datetime.now()


class EntryEngine:
    def __init__(self, kite, df_cache):
        self.kite = kite
        self.df_cache = df_cache

    def _db_connection(self):
        return mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
        )

    def _check_signal(self, df, last_sell_time=None):
        # Need at least 3 rows: 2 completed candles + 1 current forming candle
        if df is None or len(df) < 3:
            return False
        # Skip last candle (still forming) — check the 2 completed ones before it
        completed = df.iloc[-3:-1]
        return all(completed["candle_color"] == "GREEN")

    def _mark_entry(self, symbol, buy_price, buy_time, order_id, product):
        conn = self._db_connection()
        cursor = conn.cursor()
        symbols_table = getattr(config, "SYMBOLS_TABLE", "symbols_green")
        cursor.execute(
            f"UPDATE {symbols_table} SET isExecuted=1, buyprice=%s, buytime=%s, buy_order_id=%s, product=%s WHERE symbol=%s",
            (buy_price, buy_time, order_id, product, symbol),
        )
        conn.commit()
        conn.close()

    def perform_buy(self, symbol, exchange, buy_price, buy_time):
        order_id = place_real_buy(
            self.kite,
            symbol,
            quantity=getattr(config, "DEFAULT_QTY", 1),
            exchange=exchange,
            config=config,
        )

        # Only mark entry if order was actually placed
        if not order_id:
            print(f"[GREEN] BUY skipped for {symbol} — order not placed.")
            return

        final_buy_price = buy_price
        if not str(order_id).startswith("SIMULATED"):
            try:
                time.sleep(1)
                for state in reversed(self.kite.order_history(order_id)):
                    if state["status"] == "COMPLETE" and state.get("average_price"):
                        final_buy_price = float(state["average_price"])
                        break
            except Exception:
                pass

        self._mark_entry(symbol, final_buy_price, str(buy_time), str(order_id), "MIS")

    def run_cycle(self):
        now = datetime.now().strftime("%H:%M:%S")
        symbols_checked = 0
        for item in fetch_runtime_symbols(self.kite):
            symbol, token, exchange = item["symbol"], item["token"], item["exchange"]
            if not token:
                print(f"[{now}] [GREEN] ⚠️ {symbol}: instrument_token missing, skipping.")
                continue

            conn = self._db_connection()
            cursor = conn.cursor(dictionary=True)
            symbols_table = getattr(config, "SYMBOLS_TABLE", "symbols_green")
            cursor.execute(f"SELECT * FROM {symbols_table} WHERE symbol=%s", (symbol,))
            row = cursor.fetchone()
            conn.close()

            if not row or row["isExecuted"] == 1:
                continue

            symbols_checked += 1
            try:
                new_df = build_green_dataframe(self.kite, token)
                df = update_symbol_dataframe_cache(self.df_cache, symbol, new_df)
            except Exception as e:
                print(f"[{now}] [GREEN] ❌ Error fetching {symbol}: {e}")
                continue

            candles = len(df) if df is not None else 0
            if self._check_signal(df, row["last_sell_time"]):
                print(f"[{now}] [GREEN] 🟢 SIGNAL {symbol} | candles:{candles} → BUY")
                self.perform_buy(symbol, exchange, float(df.iloc[-1]["close"]), str(df.iloc[-1]["date"]))
            else:
                if df is not None and len(df) >= 3:
                    completed = df.iloc[-3:-1]
                    colors = list(completed["candle_color"])
                    print(f"[{now}] [GREEN] {symbol} | last 2: {colors} | candles:{candles}")

        cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_df_cache.pkl")
        temp_file = cache_file + ".tmp"
        with open(temp_file, "wb") as f:
            pickle.dump(self.df_cache, f)
        os.replace(temp_file, cache_file)
