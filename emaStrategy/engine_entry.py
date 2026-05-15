import os
import sys
import time
import threading
import mysql.connector
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.append(ROOT_DIR)

import st_config_ema as config
from engine_symbol_data import check_ema_entry_signal
from config.order_manager import place_real_sell

class EMAEntryEngine:
    def __init__(self, kite, df_cache):
        self.kite = kite
        self.df_cache = df_cache
        self.is_running = False

    def _get_conf(self, var_name):
        try:
            return getattr(config, var_name)
        except AttributeError as e:
            print(f"{var_name} must be present in env. {e}")
            raise e

    def _db_connection(self):
        return mysql.connector.connect(
            host=self._get_conf("DB_HOST"),
            user=self._get_conf("DB_USER"),
            password=self._get_conf("DB_PASSWORD"),
            database=self._get_conf("DB_NAME")
        )

    def start(self):
        print("[EMA-LIVE] Starting Entry Engine...")
        self.is_running = True
        threading.Thread(target=self.check_signals_loop, daemon=True).start()

    def check_signals_loop(self):
        while self.is_running:
            try:
                conn = self._db_connection()
                cursor = conn.cursor(dictionary=True)
                table = self._get_conf("EMA_SYMBOLS_LIVE_TBL")
                cursor.execute(f"SELECT symbol, instrument_token as token, exchange FROM {table} WHERE isExecuted = 0")
                pending_symbols = cursor.fetchall()
                conn.close()

                if not pending_symbols:
                    time.sleep(60)
                    continue

                for item in pending_symbols:
                    symbol, token, exchange = item['symbol'], item['token'], item['exchange']
                    
                    try:
                        df = self.df_cache.get(symbol)
                        if df is None: continue
                        
                        is_signal, trigger_price = check_ema_entry_signal(df)
                        
                        if is_signal:
                            instrument = f"{exchange}:{symbol}"
                            ltp_data = self.kite.ltp(instrument)
                            live_price = ltp_data[instrument]['last_price']
                            
                            try:
                                target_pct = config.TARGET
                            except AttributeError:
                                target_pct = 0.5
                                    
                            target_price = round(live_price * (1 - target_pct/100), 2)
                            
                            print(f"[EMA-LIVE] 🎯 {symbol} SIGNAL at {trigger_price} | Execution: {live_price}")
                            self.execute_entry(symbol, exchange, live_price, trigger_price, target_price)
                    except Exception as e:
                        print(f"[EMA-LIVE] Error for {symbol}: {e}")

                time.sleep(15)
            except Exception as e:
                print(f"[EMA-LIVE] Loop Error: {e}")
                time.sleep(30)

    def execute_entry(self, symbol, exchange, price, trigger, target):
        try:
            qty = config.DEFAULT_QTY
        except AttributeError as e:
            print(f"DEFAULT_QTY missing in env. {e}")
            raise e
            
        order_id = place_real_sell(self.kite, symbol, qty, exchange, config)
        if order_id:
            self._mark_executed(symbol, price, trigger, order_id, target)

    def _mark_executed(self, symbol, price, trigger, order_id, target):
        conn = self._db_connection()
        cursor = conn.cursor()
        table = self._get_conf("EMA_SYMBOLS_LIVE_TBL")
        cursor.execute(f"""
            UPDATE {table} 
            SET isExecuted=1, buy_price=%s, trigger_buy_price=%s, buy_time=%s, buy_order_id=%s, target_price=%s 
            WHERE symbol=%s
        """, (price, trigger, datetime.now(), order_id, target, symbol))
        conn.commit()
        conn.close()
        print(f"[EMA-LIVE] ✅ {symbol} entry marked.")

if __name__ == "__main__":
    from config.base_config import get_kite_session
    kite = get_kite_session()
    if kite:
        engine = EMAEntryEngine(kite, {})
        engine.start()
        while True: time.sleep(1)
