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
from engine_symbol_data import check_ema_entry_signal
from configuration.order_manager import place_real_sell

class EMAEntryEngine:
    def __init__(self, kite, df_cache):
        self.kite = kite
        self.df_cache = df_cache
        self.is_running = False

    def start(self):
        print("[EMA-LIVE] Starting Entry Engine...")
        self.is_running = True
        threading.Thread(target=self.check_signals_loop, daemon=True).start()

    def check_signals_loop(self):
        while self.is_running:
            try:
                table = st_config_ema.EMA_SYMBOLS_LIVE_TBL
                pending = db_fetchall(
                    f"SELECT symbol, instrument_token, exchange FROM {table} WHERE isExecuted = 0"
                )

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

                        is_signal, trigger_price = check_ema_entry_signal(df)

                        if is_signal:
                            instrument = f"{exchange}:{symbol}"
                            ltp_data = self.kite.ltp(instrument)
                            live_price = ltp_data[instrument]['last_price']

                            target_pct = getattr(st_config_ema, "EMA_TARGET", 0.5)
                            target_price = round(live_price * (1 - target_pct / 100), 2)

                            print(f"[EMA-LIVE] 🎯 {symbol} SIGNAL at {trigger_price} | Execution: {live_price}")
                            self.execute_entry(symbol, exchange, token, live_price, trigger_price, target_price)

                    except Exception as e:
                        print(f"[EMA-LIVE] Error for {symbol}: {e}")

                time.sleep(15)
            except Exception as e:
                print(f"[EMA-LIVE] Loop Error: {e}")
                time.sleep(30)

    def execute_entry(self, symbol, exchange, token, price, trigger, target):
        qty = getattr(st_config_ema, "DEFAULT_QTY", 1)
        order_id = place_real_sell(self.kite, symbol, qty, exchange, st_config_ema)
        if order_id:
            table = st_config_ema.EMA_SYMBOLS_LIVE_TBL
            db_exec(f"""
                UPDATE {table}
                SET isExecuted=1, buy_price=%s, trigger_buy_price=%s, buy_time=%s, buy_order_id=%s, target_price=%s
                WHERE instrument_token=%s
            """, (price, trigger, datetime.now(), order_id, target, token))
            print(f"[EMA-LIVE] ✅ {symbol} entry marked. Order: {order_id}")
