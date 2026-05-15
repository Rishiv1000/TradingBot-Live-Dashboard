import os
import sys
import pickle
from fastapi import APIRouter

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
if ROOT_DIR not in sys.path: sys.path.insert(0, ROOT_DIR)
if STRATEGY_DIR not in sys.path: sys.path.insert(0, STRATEGY_DIR)

from api_shared import (
    STRATEGIES, db_fetchall, db_exec, is_running,
    start_strategy_process, stop_strategy_process,
    terminate_strategy_process, SymbolRequest, TargetUpdateRequest, LOGS_DIR
)
import st_config_ema
from engine_symbol_data import build_ema_dataframe, get_ema_smart_sleep
from configuration.candle_data import search_kite_symbol

router = APIRouter(prefix="/api/ema", tags=["EMA"])

@router.get("/symbols")
def get_symbols():
    table = STRATEGIES["EMA"]["table"]
    return db_fetchall(f"SELECT * FROM {table}")

@router.post("/symbols")
def add_symbol(body: SymbolRequest):
    table = STRATEGIES["EMA"]["table"]
    from configuration.kite_session import generate_or_load_session
    kite = generate_or_load_session(st_config_ema.API_KEY, st_config_ema.ACCESS_TOKEN)
    token = search_kite_symbol(kite, body.exchange, body.symbol) if kite else None
    if not token:
        return {"success": False, "error": f"Symbol {body.symbol} not found on {body.exchange}"}
    db_exec(f"""
        INSERT INTO {table} (symbol, exchange, instrument_token, target_price)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE instrument_token=%s, target_price=%s
    """, (body.symbol.upper(), body.exchange.upper(), token, body.target_price, token, body.target_price))
    return {"success": True}

@router.delete("/symbols/{symbol}")
def delete_symbol(symbol: str):
    table = STRATEGIES["EMA"]["table"]
    db_exec(f"DELETE FROM {table} WHERE symbol=%s", (symbol.upper(),))
    return {"success": True}

@router.post("/symbols/reload-cache")
def reload_symbols():
    signal_file = os.path.join(STRATEGY_DIR, ".reload_symbols")
    with open(signal_file, "w") as f: f.write("RELOAD")
    return {"success": True}

@router.get("/df/{symbol}")
def get_df(symbol: str):
    cache_path = os.path.join(STRATEGY_DIR, "live_df_cache.pkl")
    if not os.path.exists(cache_path):
        return {"candle_count": 0, "last_candle": None, "columns": [], "data": []}
    try:
        table = STRATEGIES["EMA"]["table"]
        res = db_fetchall(f"SELECT instrument_token FROM {table} WHERE symbol=%s", (symbol.upper(),))
        if not res: return {"error": "Symbol not in DB"}
        token = res[0]['instrument_token']
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
        if token not in cache:
            return {"candle_count": 0, "last_candle": None, "columns": [], "data": []}
        df = cache[token]
        last_candle = str(df.iloc[-1]["date"]) if not df.empty and "date" in df.columns else None
        df_tail = df.tail(500).fillna("")
        return {
            "candle_count": len(df),
            "last_candle": last_candle,
            "next_candle_sec": get_ema_smart_sleep(),
            "columns": list(df_tail.columns),
            "data": df_tail.to_dict(orient="records"),
        }
    except Exception as e:
        return {"candle_count": 0, "error": str(e)}

@router.get("/positions")
def get_positions():
    table = STRATEGIES["EMA"]["table"]
    return db_fetchall(f"SELECT symbol, buy_price as buyprice, buy_time as buytime FROM {table} WHERE isExecuted=1")

@router.get("/history")
def get_history():
    return db_fetchall("SELECT 'EMA' as strategy, symbol, buy_time as buytime, buy_price as buyprice, sell_time as selltime, sell_price as sellprice, pnl, reason FROM ema_trades_live ORDER BY id DESC LIMIT 100")

@router.get("/terminal")
def get_terminal():
    log_path = os.path.join(LOGS_DIR, "ema_terminal.log")
    if not os.path.exists(log_path): return {"lines": "No log yet."}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        return {"lines": "".join(f.readlines()[-200:])}

@router.delete("/terminal")
def clear_terminal():
    log_path = os.path.join(LOGS_DIR, "ema_terminal.log")
    try: open(log_path, "w").close()
    except Exception: pass
    return {"success": True}

@router.post("/start")
def start_strategy():
    return start_strategy_process("EMA")

@router.post("/stop")
def stop_strategy():
    return stop_strategy_process("EMA")

@router.post("/terminate")
def terminate_strategy():
    return terminate_strategy_process("EMA")

@router.post("/update-target")
def update_target(body: TargetUpdateRequest):
    table = STRATEGIES["EMA"]["table"]
    db_exec(f"UPDATE {table} SET target_price=%s WHERE symbol=%s", (body.target_price, body.symbol.upper()))
    return {"success": True}
