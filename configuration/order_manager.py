import time
import os
import traceback
from dotenv import dotenv_values

def _is_real_trading_enabled(config):
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        env_vars = dotenv_values(env_path)
        return str(env_vars.get("REAL_TRADING_ENABLED", "False")).lower() == "true"
    return getattr(config, "REAL_TRADING_ENABLED", False)

def _verify_position(kite, symbol, exchange, expected_qty):
    """Verify Zerodha account actually holds expected_qty for the symbol."""
    try:
        positions = kite.positions()
        all_pos = positions.get("day", []) + positions.get("net", [])
        for pos in all_pos:
            if pos["tradingsymbol"].upper() == symbol.upper() and pos["exchange"].upper() == exchange.upper():
                actual_qty = pos["quantity"]
                ok = (actual_qty == expected_qty)
                return actual_qty, ok
        return 0, (expected_qty == 0)
    except Exception as e:
        print(f"⚠️ Position verify failed for {symbol}: {e}")
        return None, False


def place_real_buy(kite, symbol, quantity, exchange, config):
    if not _is_real_trading_enabled(config):
        print(f"🔒 [BLOCKED] Real BUY/SELL function is blocked by .env — REAL_TRADING_ENABLED=False")
        return None

    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        ltp = kite.ltp(instrument)[instrument]["last_price"]

        slippage = getattr(config, "BUY_SLIPPAGE", 0.5)
        limit_price = round(ltp * (1 + slippage / 100), 1)

        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=exchange.upper(),
            tradingsymbol=symbol.upper(),
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=quantity,
            order_type=kite.ORDER_TYPE_LIMIT,
            price=limit_price,
            product=kite.PRODUCT_MIS,
        )
        print(f"✅ BUY order placed: {symbol} @ {limit_price} (LTP={ltp}) | order_id: {order_id}")

        time.sleep(1.5)
        actual_qty, ok = _verify_position(kite, symbol, exchange, quantity)
        if ok:
            print(f"✅ Position verified: {symbol} qty={actual_qty}")
        else:
            print(f"⚠️ Position mismatch: {symbol} expected={quantity}, actual={actual_qty}")

        return order_id
    except Exception as e:
        print(f"❌ BUY order failed for {symbol}: {e}")
        print(traceback.format_exc())
        return None


def place_real_sell(kite, symbol, quantity, exchange, product, config, tag=None):
    if not _is_real_trading_enabled(config):
        print(f"🔒 [BLOCKED] Real BUY/SELL function is blocked by .env — REAL_TRADING_ENABLED=False")
        return None

    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        ltp = kite.ltp(instrument)[instrument]["last_price"]

        slippage = getattr(config, "SELL_SLIPPAGE", 0.5)
        limit_price = round(ltp * (1 - slippage / 100), 1)

        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=exchange.upper(),
            tradingsymbol=symbol.upper(),
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=quantity,
            order_type=kite.ORDER_TYPE_LIMIT,
            price=limit_price,
            product=product,
            tag=str(tag)[:20] if tag else None,
        )
        print(f"✅ SELL order placed: {symbol} @ {limit_price} (LTP={ltp}) | order_id: {order_id}")

        time.sleep(1.5)
        actual_qty, ok = _verify_position(kite, symbol, exchange, 0)
        if ok:
            print(f"✅ Position closed: {symbol} qty=0")
        else:
            print(f"⚠️ Position NOT cleared: {symbol} still showing qty={actual_qty}")

        return order_id
    except Exception as e:
        print(f"❌ SELL order failed for {symbol}: {e}")
        print(traceback.format_exc())
        return None
