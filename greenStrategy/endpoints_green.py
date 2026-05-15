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
    terminate_strategy_process, SymbolRequest, LOGS_DIR
)
import st_config_green
from configuration.candle_data import search_kite_symbol, interval_minutes

router = APIRouter(prefix="/api/green", tags=["GREEN"])

@router.get("/symbols")
def get_symbols():
    table = STRATEGIES["GREEN"]["table"]
    return db_fetchall(f"SELECT * FROM {table}")

@router.post("/symbols")
def add_symbol(body: SymbolRequest):
    table = STRATEGIES["GREEN"]["table"]
    from configuration.kite_session import generate_or_load_session
    kite = generate_or_load_session(st_config_green.API_KEY, st_config_green.ACCESS_TOKEN)
    token = search_kite_symbol(kite, body.exchange, body.symbol) if kite else None
    if not token:
        return {"success": False, "error": f"Symbol {body.symbol} not found on {body.exchange}"}
    db_exec(f"""
        INSERT INTO {table} (symbol, exchange, instrument_token)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE instrument_token=%s
    """, (body.symbol.upper(), body.exchange.upper(), token, token))
    return {"success": True}

@router.delete("/symbols/{symbol}")
def delete_symbol(symbol: str):
    table = STRATEGIES["GREEN"]["table"]
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
        table = STRATEGIES["GREEN"]["table"]
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
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        interval = interval_minutes(st_config_green.TIMEFRAME)
        remaining = (interval * 60) - ((now.hour * 60 + now.minute) % interval * 60 + now.second)
        next_candle_sec = max(0, remaining)
        return {
            "candle_count": len(df),
            "last_candle": last_candle,
            "next_candle_sec": next_candle_sec,
            "columns": list(df_tail.columns),
            "data": df_tail.to_dict(orient="records"),
        }
    except Exception as e:
        return {"candle_count": 0, "error": str(e)}

@router.get("/positions")
def get_positions():
    table = STRATEGIES["GREEN"]["table"]
    return db_fetchall(f"SELECT symbol, buyprice, buytime FROM {table} WHERE isExecuted=1")

@router.get("/history")
def get_history():
    return db_fetchall("SELECT 'GREEN' as strategy, symbol, buytime, buyprice, selltime, sellprice, pnl, reason FROM green_trades_live ORDER BY id DESC LIMIT 100")

@router.get("/terminal")
def get_terminal():
    log_path = os.path.join(LOGS_DIR, "green_terminal.log")
    if not os.path.exists(log_path): return {"lines": "No log yet."}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        return {"lines": "".join(f.readlines()[-200:])}

@router.delete("/terminal")
def clear_terminal():
    log_path = os.path.join(LOGS_DIR, "green_terminal.log")
    try: open(log_path, "w").close()
    except Exception: pass
    return {"success": True}

@router.post("/start")
def start_strategy():
    return start_strategy_process("GREEN")

@router.post("/stop")
def stop_strategy():
    return stop_strategy_process("GREEN")

@router.post("/terminate")
def terminate_strategy():
    return terminate_strategy_process("GREEN")
