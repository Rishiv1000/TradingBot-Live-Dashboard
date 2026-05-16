import os
import sys
import time
import threading
from datetime import datetime
from kiteconnect import KiteTicker

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
if STRATEGY_DIR not in sys.path: sys.path.insert(0, STRATEGY_DIR)
if ROOT_DIR not in sys.path: sys.path.insert(0, ROOT_DIR)

import st_config_ema
from api_shared import db_fetchall, db_exec
from engine_db import setup_db
from configuration.order_manager import place_real_buy

class EMAExitEngine:
    def __init__(self, kite, df_cache):
        self.kite = kite
        self.df_cache = df_cache
        self.state = {
            "open_by_token":     {},   # token → trade row
            "subscribed_tokens": set(),
            "processing":        set(),
            "lock":              threading.Lock(),
        }

    def _fetch_open_trades(self):
        table = st_config_ema.EMA_SYMBOLS_LIVE_TBL
        try:
            return db_fetchall(f"SELECT * FROM {table} WHERE isExecuted=1")
        except Exception as e:
            if "doesn't exist" in str(e).lower() or "1146" in str(e):
                print(f"[EMA-EXIT] Table {table} not found. Running setup_db...")
                setup_db()
                return db_fetchall(f"SELECT * FROM {table} WHERE isExecuted=1")
            else:
                raise e
        return []

    # ── STRATEGY EXIT LOGIC ────────────────────────────────
    def _check_exit(self, df, trade, live_price):
        """
        EMA Short Exit Conditions (Check both):
          1. TARGET HIT  — live_price <= target_price (if target_price > 0)
          2. EMA REVERSAL — EMA9 crossed above EMA20 (cross_up == 1)
        """
        target_price = float(trade.get("target_price") or 0)
        
        # 1. Target Hit?
        if target_price > 0 and live_price <= target_price:
            return True, target_price, "TARGET_HIT"
            
        # 2. EMA Reversal?
        if df is not None and len(df) >= 2:
            if df.iloc[-2].get("cross_up") == 1:
                return True, df.iloc[-2]["close"], "EMA_REVERSAL"
                
        return False, None, None

    def _refresh_subscriptions(self, kws):
        """Re-read open trades from DB and sync WebSocket subscriptions."""
        trades = self._fetch_open_trades()
        with self.state["lock"]:
            self.state["open_by_token"] = {
                row["instrument_token"]: row
                for row in trades
                if row["instrument_token"]
                and row["buy_order_id"] not in self.state["processing"]
            }
        if not kws.is_connected():
            return
        with self.state["lock"]:
            latest    = set(self.state["open_by_token"].keys())
            to_add    = list(latest - self.state["subscribed_tokens"])
            to_remove = list(self.state["subscribed_tokens"] - latest)
            if to_add:
                kws.subscribe(to_add)
                kws.set_mode(kws.MODE_FULL, to_add)
                print(f"[EMA-EXIT] 📡 Subscribed tokens: {to_add}")
            if to_remove:
                kws.unsubscribe(to_remove)
                print(f"[EMA-EXIT] 📴 Unsubscribed tokens: {to_remove}")
            self.state["subscribed_tokens"] = latest

    def _perform_exit(self, trade, live_price, trigger_price, reason):
        """Places buy-to-cover order, waits for actual fill, then logs trade."""
        symbol   = trade["symbol"]
        exchange = trade["exchange"]
        token    = trade["instrument_token"]
        qty      = getattr(st_config_ema, "DEFAULT_QTY")

        symbols_table = st_config_ema.EMA_SYMBOLS_LIVE_TBL

        # Step 1: Save trigger_sell_price immediately to DB
        db_exec(f"""
            UPDATE {symbols_table}
            SET trigger_sell_price=%s
            WHERE instrument_token=%s
        """, (trigger_price, token))
        print(f"[EMA-EXIT] 🎯 {symbol} exit triggered @ {trigger_price} | Reason: {reason}")

        order_id = place_real_buy(self.kite, symbol, qty, exchange, st_config_ema)
        if not order_id:
            print(f"[EMA-EXIT] ⚠️ Exit order failed for {symbol}.")
            with self.state["lock"]:
                self.state["processing"].discard(trade["buy_order_id"])
            return

        # Step 2: Wait for actual fill price
        actual_exit_price = live_price
        if not str(order_id).startswith("SIMULATED"):
            for attempt in range(6):
                time.sleep(2 if attempt == 0 else 3)
                try:
                    for state in reversed(self.kite.order_history(order_id)):
                        if state["status"] == "COMPLETE":
                            if state.get("average_price"):
                                actual_exit_price = float(state["average_price"])
                            break
                        elif state["status"] in ("CANCELLED", "REJECTED"):
                            print(f"[EMA-EXIT] ❌ BUY order {order_id} {state['status']} for {symbol}.")
                            with self.state["lock"]:
                                self.state["processing"].discard(trade["buy_order_id"])
                            return
                    else:
                        print(f"[EMA-EXIT] ⏳ {symbol} exit order pending (attempt {attempt+1}/6)...")
                        continue
                    break
                except Exception as e:
                    print(f"[EMA-EXIT] ⚠️ order_history error for {symbol}: {e}")

        # Step 3: Log trade with actual fill prices
        self._log_and_reset(trade, actual_exit_price, trigger_price, order_id, reason)
        with self.state["lock"]:
            self.state["processing"].discard(trade["buy_order_id"])
            self.state["open_by_token"].pop(token, None)
            self.state["subscribed_tokens"].discard(token)

    def _log_and_reset(self, trade, exit_price, trigger_price, order_id, reason):
        symbol        = trade["symbol"]
        token         = trade["instrument_token"]
        entry_price   = float(trade["sell_price"])
        trigger_entry = float(trade.get("trigger_sell_price") or entry_price)
        entry_time    = trade["sell_time"]
        entry_oid     = trade["sell_order_id"]

        pnl            = round(entry_price - exit_price, 2)   # SHORT: profit when price drops
        entry_slip     = round(entry_price - trigger_entry, 2)
        exit_slip      = round(exit_price - float(trigger_price or exit_price), 2)
        total_slippage = round(entry_slip - exit_slip, 2)

        trades_table  = st_config_ema.EMA_TRADES_LIVE_TBL
        symbols_table = st_config_ema.EMA_SYMBOLS_LIVE_TBL

        db_exec(f"""
            INSERT INTO {trades_table}
            (symbol, trigger_sell_price, sell_price, sell_time, sell_order_id,
             trigger_buy_price, buy_price, buy_time, buy_order_id,
             pnl, reason, slippage, mode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (symbol, trigger_entry, entry_price, entry_time, entry_oid,
              trigger_price, exit_price, datetime.now(), order_id,
              pnl, reason, total_slippage, "LIVE"))

        # Reset symbol state
        db_exec(f"""
            UPDATE {symbols_table}
            SET isExecuted=0, sell_price=NULL, trigger_sell_price=NULL,
                sell_time=NULL, sell_order_id=NULL, trigger_buy_price=NULL, target_price=0
            WHERE instrument_token=%s
        """, (token,))

        print(f"[EMA-EXIT] ✅ {symbol} Closed @ {exit_price} | PnL: {pnl} | Slip: ₹{total_slippage}")

    def start(self):
        """Start KiteTicker WebSocket for real-time price monitoring."""
        print("[EMA-EXIT] 🚀 Starting real-time exit monitoring via KiteTicker...")
        kws = KiteTicker(st_config_ema.API_KEY, self.kite.access_token)

        def on_ticks(_ws, ticks):
            for tick in ticks:
                token      = tick["instrument_token"]
                live_price = float(tick["last_price"])

                row_to_exit  = None
                exit_reason  = None
                trigger_p    = None

                with self.state["lock"]:
                    trade = self.state["open_by_token"].get(token)
                    if trade and trade["buy_order_id"] not in self.state["processing"]:
                        df = self.df_cache.get(token)
                        is_exit, trigger_price, reason = self._check_exit(df, trade, live_price)
                        if is_exit:
                            self.state["processing"].add(trade["buy_order_id"])
                            row_to_exit = trade
                            exit_reason = reason
                            trigger_p   = trigger_price

                if row_to_exit:
                    print(f"[EMA-EXIT] 🔔 {row_to_exit['symbol']} EXIT: {exit_reason} @ {live_price}")
                    threading.Thread(
                        target=self._perform_exit,
                        args=(row_to_exit, live_price, trigger_p, exit_reason),
                        daemon=True,
                    ).start()

        def on_connect(ws, _res):
            print("[EMA-EXIT] 🔗 KiteTicker connected.")
            self._refresh_subscriptions(ws)

        def on_close(ws, code, reason):
            print(f"[EMA-EXIT] ❌ KiteTicker closed: {code} {reason}")

        kws.on_ticks  = on_ticks
        kws.on_connect = on_connect
        kws.on_close  = on_close
        kws.connect(threaded=True)

        # Main loop: refresh DB subscriptions every 2 seconds
        while True:
            self._refresh_subscriptions(kws)
            time.sleep(2)
