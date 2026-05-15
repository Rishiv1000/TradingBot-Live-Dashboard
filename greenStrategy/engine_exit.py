import os
import sys
import threading
import time
from datetime import datetime

from kiteconnect import KiteTicker

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
if STRATEGY_DIR not in sys.path: sys.path.insert(0, STRATEGY_DIR)
if ROOT_DIR not in sys.path: sys.path.insert(0, ROOT_DIR)

import st_config_green
from api_shared import db_fetchall, db_exec
from configuration.order_manager import place_real_sell

SYMBOLS_TABLE = getattr(st_config_green, "SYMBOLS_TABLE", "green_symbols_live")


class ExitEngine:
    def __init__(self, kite):
        self.kite = kite
        self.target_pct   = getattr(st_config_green, "TARGET", 0.5)
        self.stoploss_pct = getattr(st_config_green, "STOPLOSS", 0.5)
        self.state = {
            "open_by_token":    {},
            "subscribed_tokens": set(),
            "processing":       set(),
            "lock":             threading.Lock(),
        }

    def _fetch_open_positions(self):
        return db_fetchall(f"SELECT * FROM {SYMBOLS_TABLE} WHERE isExecuted=1")

    def _should_exit(self, buy_price, ltp):
        pnl_pct = ((ltp - buy_price) / buy_price) * 100
        if pnl_pct >= self.target_pct:   return True, "TARGET HIT"
        if pnl_pct <= -self.stoploss_pct: return True, "STOPLOSS HIT"
        return False, ""

    def _close_position_and_log(self, row, sell_price, reason, sell_order_id, ltp_at_sell=None):
        buy_price      = float(row["buyprice"])
        token          = row.get("instrument_token")
        qty            = getattr(st_config_green, "DEFAULT_QTY", 1)
        pnl            = round((sell_price - buy_price) * qty, 2)
        buy_slippage   = round(buy_price - float(row.get("signal_price") or buy_price), 2)
        sell_slippage  = round((ltp_at_sell or sell_price) - sell_price, 2)
        total_slippage = round(buy_slippage + sell_slippage, 2)

        print(f"[GREEN] 📊 {row['symbol']} slippage → BUY: ₹{buy_slippage} | SELL: ₹{sell_slippage} | TOTAL: ₹{total_slippage}")

        db_exec(
            "INSERT INTO trades_log (symbol, buytime, buyprice, selltime, sellprice, pnl, reason, slippage, buy_order_id, sell_order_id, strategy) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (row["symbol"], row["buytime"], row["buyprice"], datetime.now(),
             sell_price, pnl, reason, total_slippage,
             str(row["buy_order_id"]), str(sell_order_id), st_config_green.STRATEGY_NAME)
        )
        db_exec(
            f"UPDATE {SYMBOLS_TABLE} SET isExecuted=0, buyprice=NULL, buytime=NULL, buy_order_id=NULL, product=NULL, last_sell_time=%s WHERE instrument_token=%s",
            (datetime.now(), token)
        )

        with self.state["lock"]:
            if token:
                self.state["open_by_token"].pop(token, None)
                self.state["subscribed_tokens"].discard(token)

        print(f"[GREEN] SOLD {row['symbol']} @ {sell_price} ({reason}) | PnL: ₹{round(pnl, 2)}")

    def _place_sell(self, row):
        order_id = str(row["buy_order_id"])

        if order_id.startswith("SIMULATED"):
            return place_real_sell(
                self.kite, row["symbol"],
                quantity=getattr(st_config_green, "DEFAULT_QTY", 1),
                exchange=getattr(st_config_green, "LIVE_EXCHANGE", "NSE"),
                product="MIS", config=st_config_green, tag=order_id,
            )

        try:
            if order_id == "FAILED_OR_REJECTED":
                print(f"[GREEN] Cleaning up failed entry for {row['symbol']}.")
                return "CLEANUP"
            orders = self.kite.orders()
            order  = next((o for o in orders if str(o["order_id"]) == order_id), None)
            if not order:
                print(f"[GREEN] Order {order_id} not found in Zerodha.")
                return None
            return place_real_sell(
                self.kite, order["tradingsymbol"], order["quantity"],
                order["exchange"], order["product"], config=st_config_green, tag=order_id,
            )
        except Exception as e:
            print(f"[GREEN] Exit failed: {e}")
            return None

    def _refresh_positions(self, kws):
        positions = self._fetch_open_positions()
        with self.state["lock"]:
            self.state["open_by_token"] = {
                row["instrument_token"]: row
                for row in positions
                if row["instrument_token"] and row["buy_order_id"] not in self.state["processing"]
            }
        if kws.is_connected():
            with self.state["lock"]:
                latest   = set(self.state["open_by_token"].keys())
                to_add   = list(latest - self.state["subscribed_tokens"])
                to_remove = list(self.state["subscribed_tokens"] - latest)
                if to_add:
                    kws.subscribe(to_add)
                    kws.set_mode(kws.MODE_FULL, to_add)
                if to_remove:
                    kws.unsubscribe(to_remove)
                self.state["subscribed_tokens"] = latest

    def _perform_sell(self, row, ltp, reason):
        exit_order_id = self._place_sell(row)
        if not exit_order_id:
            with self.state["lock"]:
                self.state["processing"].discard(row["buy_order_id"])
            return

        if exit_order_id == "CLEANUP":
            db_exec(
                f"UPDATE {SYMBOLS_TABLE} SET isExecuted=0, buyprice=NULL, buytime=NULL, buy_order_id=NULL, product=NULL, last_sell_time=%s WHERE symbol=%s",
                (datetime.now(), row["symbol"])
            )
            with self.state["lock"]:
                self.state["processing"].discard(row["buy_order_id"])
            return

        sell_price = ltp
        if not str(exit_order_id).startswith("SIMULATED"):
            try:
                for state in reversed(self.kite.order_history(exit_order_id)):
                    if state["status"] == "COMPLETE" and state.get("average_price"):
                        sell_price = float(state["average_price"])
                        break
            except Exception:
                pass

        self._close_position_and_log(row, sell_price, reason, exit_order_id, ltp)
        with self.state["lock"]:
            self.state["processing"].discard(row["buy_order_id"])

    def start_monitoring(self):
        kws = KiteTicker(st_config_green.API_KEY, self.kite.access_token)

        def on_ticks(_ws, ticks):
            for tick in ticks:
                token      = tick["instrument_token"]
                ltp        = float(tick["last_price"])
                row_to_sell = None
                with self.state["lock"]:
                    row = self.state["open_by_token"].get(token)
                    if row and row["buy_order_id"] not in self.state["processing"]:
                        should_exit, reason = self._should_exit(float(row["buyprice"]), ltp)
                        if should_exit:
                            self.state["processing"].add(row["buy_order_id"])
                            row_to_sell  = row
                            exit_reason  = reason
                if row_to_sell:
                    self._perform_sell(row_to_sell, ltp, exit_reason)

        kws.on_ticks  = on_ticks
        kws.on_connect = lambda ws, _res: self._refresh_positions(ws)
        kws.connect(threaded=True)
        while True:
            self._refresh_positions(kws)
            time.sleep(0.5)
