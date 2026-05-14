import os
import sys
import time
import threading
import mysql.connector
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.append(ROOT_DIR)

import st_config as config
from engine_symbol_data import check_ema_exit_signal
from config.order_manager import place_real_buy

class EMAExitEngine:
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
        print("[EMA-EXIT-LIVE] Starting Exit Engine...")
        self.is_running = True
        threading.Thread(target=self.check_exits_loop, daemon=True).start()

    def check_exits_loop(self):
        while self.is_running:
            try:
                conn = self._db_connection()
                cursor = conn.cursor(dictionary=True)
                table = self._get_conf("EMA_SYMBOLS_LIVE_TBL")
                cursor.execute(f"SELECT * FROM {table} WHERE isExecuted = 1")
                active_trades = cursor.fetchall()
                conn.close()

                if not active_trades:
                    time.sleep(30)
                    continue

                for trade in active_trades:
                    symbol = trade['symbol']
                    exchange = trade['exchange']

                    try:
                        instrument = f"{exchange}:{symbol}"
                        ltp_data = self.kite.ltp(instrument)
                        live_price = ltp_data[instrument]['last_price']

                        df = self.df_cache.get(symbol)
                        is_exit, trigger_price, reason = check_ema_exit_signal(df, trade, live_price)

                        if is_exit:
                            print(f"[EMA-EXIT] 🔔 {symbol} EXIT: {reason} at {live_price}")
                            self.execute_exit(trade, live_price, trigger_price, reason)
                    except Exception as e:
                        print(f"[EMA-EXIT] Error for {symbol}: {e}")

                time.sleep(15)
            except Exception as e:
                print(f"[EMA-EXIT] Loop Error: {e}")
                time.sleep(30)

    def execute_exit(self, trade, price, trigger, reason):
        symbol = trade['symbol']
        exchange = trade['exchange']
        try:
            qty = config.DEFAULT_QTY
        except AttributeError as e:
            print(f"DEFAULT_QTY missing in env. {e}")
            raise e
            
        order_id = place_real_buy(self.kite, symbol, qty, exchange, config)
        if order_id:
            self._log_and_reset(trade, price, trigger, order_id, reason)

    def _log_and_reset(self, trade, exit_price, trigger_exit, order_id, reason):
        symbol = trade['symbol']
        entry_price = trade['buy_price']
        trigger_entry = trade['trigger_buy_price']
        entry_time = trade['buy_time']
        entry_order_id = trade['buy_order_id']
        
        pnl = round(entry_price - exit_price, 2)
        entry_slip = entry_price - (trigger_entry if trigger_entry else entry_price)
        exit_slip = exit_price - trigger_exit
        # For Short: Total Slippage = (ActualEntry - TriggerEntry) - (ActualExit - TriggerExit)
        total_slippage = round(entry_slip - exit_slip, 2)

        conn = self._db_connection()
        cursor = conn.cursor()
        trades_table = self._get_conf("EMA_TRADES_LIVE_TBL")
        cursor.execute(f"""
            INSERT INTO {trades_table} 
            (symbol, trigger_buy_price, buy_price, buy_time, trigger_sell_price, sell_price, sell_time, pnl, reason, slippage, buy_order_id, sell_order_id, strategy)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (symbol, trigger_entry, entry_price, entry_time, trigger_exit, exit_price, datetime.now(), pnl, reason, total_slippage, entry_order_id, order_id, 'EMA'))
        
        symbols_table = self._get_conf("EMA_SYMBOLS_LIVE_TBL")
        cursor.execute(f"UPDATE {symbols_table} SET isExecuted=0, buy_price=NULL, trigger_buy_price=NULL, buy_time=NULL, buy_order_id=NULL, target_price=0 WHERE symbol=%s", (symbol,))
        
        conn.commit()
        conn.close()
        print(f"[EMA-EXIT] ✅ {symbol} Exit logged. PnL: {pnl}")

if __name__ == "__main__":
    from config.base_config import get_kite_session
    kite = get_kite_session()
    if kite:
        engine = EMAExitEngine(kite, {})
        engine.start()
        while True: time.sleep(1)
