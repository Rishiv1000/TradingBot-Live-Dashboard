import os
import pickle
import sys
import time
import threading
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
if STRATEGY_DIR not in sys.path: sys.path.insert(0, STRATEGY_DIR)
if ROOT_DIR not in sys.path: sys.path.insert(0, ROOT_DIR)

import st_config_green
from api_shared import db_fetchall, db_exec
from engine_symbol_data import build_green_dataframe, refresh_all_green_data
from engine_db import setup_table
from configuration.order_manager import place_real_buy

BOT_START_TIME = datetime.now()
SYMBOLS_TABLE  = getattr(st_config_green, "SYMBOLS_TABLE", "green_symbols_live")


class EntryEngine:
    def __init__(self, kite, df_cache):
        self.kite = kite
        self.df_cache = df_cache
        self._rejected_until: dict = {}
        self.REJECTION_COOLDOWN_SEC = 300
        self._failed_signal: dict = {}

    def start(self):
        print("[GREEN-LIVE] Starting Entry Engine...")
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                print(f"[GREEN-ENTRY] Loop error: {e}")
            time.sleep(15)

    def _is_in_cooldown(self, symbol) -> bool:
        until = self._rejected_until.get(symbol)
        if until and time.time() < until:
            remaining = int(until - time.time())
            print(f"[GREEN] ⏸️ {symbol} in rejection cooldown — {remaining}s remaining.")
            return True
        return False

    def _set_cooldown(self, symbol):
        self._rejected_until[symbol] = time.time() + self.REJECTION_COOLDOWN_SEC
        print(f"[GREEN] ⏸️ {symbol} cooldown set for {self.REJECTION_COOLDOWN_SEC}s.")

    def _check_signal(self, symbol, df, last_sell_time=None):
        if df is None or len(df) < 3:
            return False
        completed = df.iloc[-3:-1]
        signal_ts = str(df.iloc[-2]["date"]) if "date" in df.columns else None
        if signal_ts and self._failed_signal.get(symbol) == signal_ts:
            print(f"[GREEN] ⏭️ {symbol} — same signal already attempted ({signal_ts}).")
            return False
        if not all(completed["candle_color"] == "GREEN"):
            return False
        self._failed_signal.pop(symbol, None)
        return True

    def _mark_entry(self, symbol, token, buy_price, buy_time, order_id, product):
        db_exec(
            f"UPDATE {SYMBOLS_TABLE} SET isExecuted=1, buyprice=%s, buytime=%s, buy_order_id=%s, product=%s WHERE instrument_token=%s",
            (buy_price, buy_time, order_id, product, token)
        )

    def _verify_and_mark(self, symbol, token, exchange, order_id, buy_price, signal_time):
        try:
            final_buy_price = buy_price
            order_filled = False
            for attempt in range(6):
                time.sleep(2 if attempt == 0 else 3)
                for state in reversed(self.kite.order_history(order_id)):
                    if state["status"] == "COMPLETE":
                        order_filled = True
                        if state.get("average_price"):
                            final_buy_price = float(state["average_price"])
                        break
                    elif state["status"] in ("CANCELLED", "REJECTED"):
                        print(f"[GREEN] ❌ BUY order {order_id} {state['status']} for {symbol}.")
                        self._failed_signal[symbol] = str(signal_time)
                        self._set_cooldown(symbol)
                        return
                if order_filled:
                    break
                print(f"[GREEN] ⏳ {symbol} order pending (attempt {attempt+1}/6)...")

            if not order_filled:
                print(f"[GREEN] ⚠️ {symbol} order not filled after retries.")
                self._failed_signal[symbol] = str(signal_time)
                return

            self._mark_entry(symbol, token, final_buy_price, str(signal_time), str(order_id), "MIS")
            buy_slippage = round(final_buy_price - buy_price, 2)
            print(f"[GREEN] ✅ Entry marked: {symbol} @ {final_buy_price} | BUY slippage: ₹{buy_slippage}")
        except Exception as e:
            print(f"[GREEN] ⚠️ Verify failed for {symbol}: {e} — marking entry to be safe.")
            self._mark_entry(symbol, token, buy_price, str(signal_time), str(order_id), "MIS")

    def perform_buy(self, symbol, token, exchange, buy_price, signal_time):
        order_id = place_real_buy(
            self.kite,
            symbol,
            quantity=getattr(st_config_green, "DEFAULT_QTY", 1),
            exchange=exchange,
            config=st_config_green,
        )
        if not order_id:
            print(f"[GREEN] BUY skipped for {symbol}.")
            self._failed_signal[symbol] = str(signal_time)
            return

        if str(order_id).startswith("SIMULATED"):
            self._mark_entry(symbol, token, buy_price, str(signal_time), str(order_id), "MIS")
            return

        threading.Thread(
            target=self._verify_and_mark,
            args=(symbol, token, exchange, order_id, buy_price, signal_time),
            daemon=True,
        ).start()
        print(f"[GREEN] 🔄 {symbol} order {order_id} placed — verifying in background...")

    def run_cycle(self):
        now = datetime.now().strftime("%H:%M:%S")

        # Single DB query — all symbols
        try:
            all_rows_list = db_fetchall(f"SELECT * FROM {SYMBOLS_TABLE}")
        except Exception as e:
            if "doesn't exist" in str(e).lower() or "1146" in str(e):
                print(f"[GREEN-LIVE] Table {SYMBOLS_TABLE} not found. Running setup_table...")
                setup_table()
                all_rows_list = db_fetchall(f"SELECT * FROM {SYMBOLS_TABLE}")
            else:
                raise e
        all_rows = {r["symbol"]: r for r in all_rows_list}

        for symbol, row in all_rows.items():
            token    = row.get("instrument_token")
            exchange = row.get("exchange", "NSE")

            if not token:
                print(f"[{now}] [GREEN] ⚠️ {symbol}: token missing, skipping.")
                continue
            if row.get("isExecuted") == 1:
                continue
            if self._is_in_cooldown(symbol):
                continue

            try:
                df = self.df_cache.get(token)
                if df is None or df.empty:
                    continue
            except Exception as e:
                print(f"[{now}] [GREEN] ❌ Cache error {symbol}: {e}")
                continue

            if self._check_signal(symbol, df, row.get("last_sell_time")):
                candles = len(df)
                print(f"[{now}] [GREEN] 🟢 SIGNAL {symbol} | candles:{candles} → BUY")
                self.perform_buy(symbol, token, exchange, float(df.iloc[-1]["close"]), str(df.iloc[-1]["date"]))
            else:
                if df is not None and len(df) >= 3:
                    colors = list(df.iloc[-3:-1]["candle_color"])
                    print(f"[{now}] [GREEN] {symbol} | last 2: {colors} | candles:{len(df)}")

        # Save token-keyed PKL
        try:
            cache_file = os.path.join(STRATEGY_DIR, "live_df_cache.pkl")
            tmp = cache_file + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(self.df_cache, f)
            os.replace(tmp, cache_file)
        except Exception as e:
            print(f"[GREEN] ⚠️ PKL save error: {e}")
