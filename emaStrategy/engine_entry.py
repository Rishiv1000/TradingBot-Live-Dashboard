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
from api_shared import db_fetchall, db_exec
from engine_db import setup_db
from configuration.order_manager import place_real_sell

class EMAEntryEngine:
    def __init__(self, kite, df_cache):
        self.kite = kite
        self.df_cache = df_cache
        self.is_running = False

    # ── STRATEGY SIGNAL ───────────────────────────────────────
    def _check_signal(self, df):
        """
        EMA Short Entry Signal:
          - EMA9 is below EMA20 (Bearish trend)
          - Gap % = (EMA20 - EMA9) / EMA9 >= EMA_SHORT_GAP threshold
        Returns: (signal: bool, trigger_price: float)
        """
        if df is None or len(df) < 2:
            return False, None

        candle = df.iloc[-2]                          # Last completed candle
        ema9    = candle["EMA_9"]
        ema20   = candle["EMA_20"]
        
        # Condition 1: EMA9 is below EMA20 (Bearish)
        if ema9 >= ema20:
            return False, None

        # Condition 2: Gap between EMA20 and EMA9 is large enough
        gap_pct = ((ema20 - ema9) / ema9) * 100

        if gap_pct >= getattr(st_config_ema, "EMA_SHORT_GAP", 0.5):
            return True, candle["close"]              # Trigger = candle close price

        return False, None

    def start(self):
        print("[EMA-LIVE] Starting Entry Engine...")
        self.is_running = True
        threading.Thread(target=self.check_signals_loop, daemon=True).start()

    def check_signals_loop(self):
        while self.is_running:
            try:
                table = st_config_ema.EMA_SYMBOLS_LIVE_TBL
                try:
                    pending = db_fetchall(
                        f"SELECT symbol, instrument_token, exchange FROM {table} WHERE isExecuted = 0"
                    )
                except Exception as e:
                    if "doesn't exist" in str(e).lower() or "1146" in str(e):
                        print(f"[EMA-LIVE] Table {table} not found. Running setup_db...")
                        setup_db()
                        pending = db_fetchall(
                            f"SELECT symbol, instrument_token, exchange FROM {table} WHERE isExecuted = 0"
                        )
                    else:
                        raise e

                if not pending:
                    time.sleep(60)
                    continue

                for item in pending:
                    symbol = item['symbol']
                    token  = item['instrument_token']
                    exchange = item['exchange']

                    if not token: continue

                    try:
                        # Token-based cache lookup
                        df = self.df_cache.get(token)
                        if df is None or df.empty: continue

                        is_signal, trigger_price = self._check_signal(df)

                        if is_signal:
                            instrument = f"{exchange}:{symbol}"
                            ltp_data = self.kite.ltp(instrument)
                            live_price = ltp_data[instrument]['last_price']

                            print(f"[EMA-LIVE] 🎯 {symbol} SIGNAL at {trigger_price} | Execution: {live_price}")
                            self.execute_entry(symbol, exchange, token, live_price, trigger_price, 0)

                    except Exception as e:
                        print(f"[EMA-LIVE] Error for {symbol}: {e}")

                time.sleep(15)
            except Exception as e:
                print(f"[EMA-LIVE] Loop Error: {e}")
                time.sleep(30)

    def execute_entry(self, symbol, exchange, token, price, trigger, target):
        qty   = getattr(st_config_ema, "DEFAULT_QTY")
        table = st_config_ema.EMA_SYMBOLS_LIVE_TBL

        order_id = place_real_sell(
            self.kite, symbol, qty, exchange,
            product="MIS",
            config=st_config_ema
        )
        if not order_id:
            print(f"[EMA-LIVE] ⚠️ SELL order skipped for {symbol}.")
            return

        # Step 1: Save trigger_sell_price immediately so dashboard shows the signal
        db_exec(f"""
            UPDATE {table}
            SET isExecuted=1, trigger_sell_price=%s, sell_price=%s,
                sell_time=%s, sell_order_id=%s, target_price=%s
            WHERE instrument_token=%s
        """, (trigger, price, datetime.now(), order_id, target, token))
        print(f"[EMA-LIVE] 🎯 {symbol} SIGNAL: {trigger} | Execution: {price} | Order: {order_id}")

        # Step 2: Wait for actual fill in background and update sell_price
        if not str(order_id).startswith("SIMULATED"):
            threading.Thread(
                target=self._verify_and_update,
                args=(symbol, token, order_id, price, trigger),
                daemon=True
            ).start()

    def _verify_and_update(self, symbol, token, order_id, estimated_price, trigger_price):
        """Wait for order fill and update actual sell price in DB."""
        table = st_config_ema.EMA_SYMBOLS_LIVE_TBL
        actual_price = estimated_price

        for attempt in range(6):
            time.sleep(2 if attempt == 0 else 3)
            try:
                for state in reversed(self.kite.order_history(order_id)):
                    if state["status"] == "COMPLETE":
                        if state.get("average_price"):
                            actual_price = float(state["average_price"])
                        break
                    elif state["status"] in ("CANCELLED", "REJECTED"):
                        print(f"[EMA-LIVE] ❌ Entry order {order_id} {state['status']} for {symbol}.")
                        db_exec(f"UPDATE {table} SET isExecuted=0, sell_price=NULL, trigger_sell_price=NULL, sell_time=NULL, sell_order_id=NULL WHERE instrument_token=%s", (token,))
                        return
                else:
                    continue
                break
            except Exception as e:
                print(f"[EMA-LIVE] ⚠️ History error {symbol}: {e}")

        # Update with actual fill price
        db_exec(f"UPDATE {table} SET sell_price=%s WHERE instrument_token=%s", (actual_price, token))
        slippage = round(actual_price - trigger_price, 2)
        print(f"[EMA-LIVE] ✅ {symbol} Actual Fill: {actual_price} | Trigger: {trigger_price} | Slip: ₹{slippage}")

