import os
import pickle
import subprocess
import sys
import time as _time
from typing import Optional

import mysql.connector
import psutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


try:
    from configuration.base_config import (
        API_KEY, API_SECRET, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME,
        ACCESS_TOKEN_FILE, LOGS_DIR, REAL_TRADING_ENABLED
    )
    print("✅ Configuration loaded successfully.")
except Exception as e:
    print(f"❌ ERROR: Failed to load configuration from base_config.py: {e}")
    API_KEY = API_SECRET = DB_HOST = DB_USER = DB_PASSWORD = DB_NAME = ""
    ACCESS_TOKEN_FILE = LOGS_DIR = ""
    REAL_TRADING_ENABLED = False

def strategy_folder(*names):
    for name in names:
        path = os.path.abspath(os.path.join(BASE_DIR, name))
        if os.path.exists(path):
            return path
    return os.path.abspath(os.path.join(BASE_DIR, names[0]))


EMA_FOLDER = strategy_folder("emaStrategy")
GREEN_FOLDER = strategy_folder("greenStrategy")


STRATEGIES = {
     "EMA": {
        "folder": EMA_FOLDER,
        "runner": os.path.join(EMA_FOLDER, "main_runner.py"),
        "table":  "ema_symbols_live",
        "color":  "#ff9800",
    },
    "GREEN": {
        "folder": GREEN_FOLDER,
        "runner": os.path.join(GREEN_FOLDER, "main_runner.py"),
        "table":  "green_symbols_live",
        "color":  "#2ea043",
    },
}

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="MultiStrategy Live API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB connection ─────────────────────────────────────────────────────────────
def _db():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        connection_timeout=10
    )


def db_fetchall(query: str, params=()):
    conn = None
    try:
        conn = _db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        if conn: conn.close()


def db_exec(query: str, params=()):
    conn = None
    try:
        conn = _db()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
    finally:
        if conn: conn.close()


def db_scalar(query: str, params=()):
    conn = _db()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        r = cursor.fetchone()
        return r[0] if r else 0
    finally:
        conn.close()


# ── Kite helpers ──────────────────────────────────────────────────────────────
def get_kite():
    if not API_KEY or not os.path.exists(ACCESS_TOKEN_FILE): return None
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=API_KEY, timeout=10)
        with open(ACCESS_TOKEN_FILE) as f: tok = f.read().strip()
        if not tok: return None
        kite.set_access_token(tok)
        return kite
    except Exception: return None


def kite_logged_in() -> bool:
    kite = get_kite()
    if not kite: return False
    try:
        kite.profile()
        return True
    except Exception: return False


# ── Process helpers ───────────────────────────────────────────────────────────
_proc_cache: dict = {}
_proc_cache_ts: float = 0.0
_PROC_CACHE_TTL = 2.0

def _get_proc_cache() -> dict:
    global _proc_cache, _proc_cache_ts
    now = _time.monotonic()
    if now - _proc_cache_ts > _PROC_CACHE_TTL:
        found = {name: None for name in STRATEGIES}
        for p in psutil.process_iter(["pid", "cmdline", "status"]):
            try:
                cmd = " ".join(p.info.get("cmdline") or [])
                for name, meta in STRATEGIES.items():
                    if meta["runner"] in cmd:
                        found[name] = p
                        break
            except: pass
        _proc_cache = found
        _proc_cache_ts = now
    return _proc_cache

def is_running(strategy: str) -> bool:
    return _get_proc_cache().get(strategy) is not None


# ── Pydantic models ───────────────────────────────────────────────────────────
class SessionRequest(BaseModel): request_token: str
class SymbolRequest(BaseModel): symbol: str; exchange: str = "NSE"; target_price: float = 0.0
class TargetUpdateRequest(BaseModel): symbol: str; target_price: float
class TradingConfigRequest(BaseModel): real_trading_enabled: bool

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/api/db/status")
def get_db_status():
    try:
        conn = _db(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW STATUS LIKE 'Threads_connected'"); connected = cursor.fetchone()["Value"]
        cursor.execute("SHOW STATUS LIKE 'Threads_running'"); running = cursor.fetchone()["Value"]
        conn.close()
        return {"status": "connected", "threads_connected": connected, "threads_running": running, "db_name": DB_NAME}
    except Exception as e: return {"status": "error", "error": str(e)}

@app.get("/api/status")
def get_status():
    cache = _get_proc_cache()
    result = {}
    for strategy, meta in STRATEGIES.items():
        try:
            conn = _db(); cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {meta['table']}"); sym_count = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM {meta['table']} WHERE isExecuted=1"); open_count = cur.fetchone()[0]
            conn.close()
        except: sym_count = open_count = 0
        result[strategy] = {
            "running": cache.get(strategy) is not None,
            "symbol_count": sym_count,
            "open_count": open_count,
            "color": meta["color"],
            "trading_enabled": REAL_TRADING_ENABLED,
        }
    return result

@app.get("/api/kite/status")
def kite_status(): return {"logged_in": kite_logged_in()}

@app.get("/api/kite/login_url")
def kite_login_url():
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not configured")
    from kiteconnect import KiteConnect
    return {"url": KiteConnect(api_key=API_KEY).login_url()}

@app.get("/api/config/trading")
def get_trading_config():
    return {"real_trading_enabled": REAL_TRADING_ENABLED}

@app.post("/api/config/trading")
def update_trading_config(body: TradingConfigRequest):
    global REAL_TRADING_ENABLED
    try:
        config_path = os.path.join(BASE_DIR, "configuration", "base_config.py")
        with open(config_path, "r") as f:
            lines = f.readlines()
        
        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith("REAL_TRADING_ENABLED"):
                new_lines.append(f"REAL_TRADING_ENABLED = {body.real_trading_enabled}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"REAL_TRADING_ENABLED = {body.real_trading_enabled}\n")
            
        with open(config_path, "w") as f:
            f.writelines(new_lines)
            
        REAL_TRADING_ENABLED = body.real_trading_enabled
        return {"success": True, "real_trading_enabled": REAL_TRADING_ENABLED}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kite/session")
def kite_session(body: SessionRequest):
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=API_KEY)
        data = kite.generate_session(body.request_token, api_secret=API_SECRET)
        with open(ACCESS_TOKEN_FILE, "w") as f: f.write(data["access_token"])
        return {"success": True}
    except Exception as e: return {"success": False, "error": str(e)}

@app.post("/api/set-defaults")
def set_defaults():
    kite = get_kite()
    if not kite:
        raise HTTPException(status_code=401, detail="Kite session missing")
    updated = 0
    errors = []
    for strategy, meta in STRATEGIES.items():
        table = meta["table"]
        try:
            rows = db_fetchall(
                f"SELECT symbol, exchange, instrument_token FROM {table} "
                "WHERE instrument_token IS NULL OR instrument_token=0"
            )
            for row in rows:
                symbol = row["symbol"].upper()
                exchange = (row.get("exchange") or "NSE").upper()
                inst = f"{exchange}:{symbol}"
                token = kite.ltp(inst)[inst]["instrument_token"]
                db_exec(
                    f"UPDATE {table} SET exchange=%s, instrument_token=%s WHERE symbol=%s",
                    (exchange, token, symbol),
                )
                updated += 1
        except Exception as e:
            errors.append(f"{strategy}: {e}")
    return {"success": not errors, "updated": updated, "error": "; ".join(errors) if errors else ""}

@app.get("/api/logs/backend")
def get_backend_logs():
    log_path = os.path.join(LOGS_DIR, "api.log")
    if not os.path.exists(log_path): return {"lines": "No backend log found."}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"lines": "".join(lines[-200:]) or "Log is empty."}
    except Exception as e:
        return {"lines": f"Error: {e}"}

@app.get("/api/logs/frontend")
def get_frontend_logs():
    log_path = os.path.join(LOGS_DIR, "vite.log")
    if not os.path.exists(log_path): return {"lines": "No frontend log found."}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"lines": "".join(lines[-200:]) or "Log is empty."}
    except Exception as e:
        return {"lines": f"Error: {e}"}

def get_symbols(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES: raise HTTPException(status_code=404)
    target_expr = "target_price" if strategy == "EMA" else "0 AS target_price"
    return db_fetchall(f"SELECT symbol, exchange, instrument_token, isExecuted, {target_expr} FROM {STRATEGIES[strategy]['table']} ORDER BY symbol")

def add_symbol(strategy: str, body: SymbolRequest):
    strategy = strategy.upper(); kite = get_kite()
    if not kite: raise HTTPException(status_code=401)
    inst = f"{body.exchange.upper()}:{body.symbol.upper()}"
    token = kite.ltp(inst)[inst]["instrument_token"]
    table = STRATEGIES[strategy]["table"]
    if strategy == "EMA":
        db_exec(f"INSERT INTO {table} (symbol, exchange, instrument_token, isExecuted, target_price) VALUES (%s, %s, %s, 0, %s) ON DUPLICATE KEY UPDATE exchange=%s, instrument_token=%s, target_price=%s",
                (body.symbol.upper(), body.exchange.upper(), token, body.target_price, body.exchange.upper(), token, body.target_price))
    else:
        db_exec(f"INSERT INTO {table} (symbol, exchange, instrument_token, isExecuted) VALUES (%s, %s, %s, 0) ON DUPLICATE KEY UPDATE exchange=%s, instrument_token=%s",
                (body.symbol.upper(), body.exchange.upper(), token, body.exchange.upper(), token))
    return {"success": True}

def update_target_price(strategy: str, body: TargetUpdateRequest):
    strategy = strategy.upper()
    if strategy not in STRATEGIES: raise HTTPException(status_code=404)
    db_exec(f"UPDATE {STRATEGIES[strategy]['table']} SET target_price=%s WHERE symbol=%s", (body.target_price, body.symbol.upper()))
    return {"success": True}

def delete_symbol(strategy: str, symbol: str):
    db_exec(f"DELETE FROM {STRATEGIES[strategy.upper()]['table']} WHERE symbol=%s", (symbol.upper(),))
    return {"success": True}

def reload_symbol_cache(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES: raise HTTPException(status_code=404)
    signal_file = os.path.join(STRATEGIES[strategy]["folder"], ".reload_symbols")
    try:
        open(signal_file, "w").close()
        return {"success": True, "message": f"{strategy} will reload symbols on next cycle."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_df(strategy: str, symbol: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES: raise HTTPException(status_code=404)
    cache_path = os.path.join(STRATEGIES[strategy]["folder"], "live_df_cache.pkl")
    if not os.path.exists(cache_path):
        return {"candle_count": 0, "last_candle": None, "columns": [], "data": []}
    try:
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
        if symbol.upper() not in cache:
            return {"candle_count": 0, "last_candle": None, "columns": [], "data": []}
        df = cache[symbol.upper()]
        last_candle = str(df.iloc[-1]["date"]) if not df.empty and "date" in df.columns else None
        df_tail = df.tail(500).fillna("")
        return {"candle_count": len(df), "last_candle": last_candle, "columns": list(df_tail.columns), "data": df_tail.to_dict(orient="records")}
    except Exception as e:
        return {"candle_count": 0, "last_candle": None, "columns": [], "data": [], "error": str(e)}

@app.get("/api/positions")
def get_positions():
    rows = []
    for strategy, meta in STRATEGIES.items():
        res = db_fetchall(f"SELECT symbol, buy_price as buyprice, buy_time as buytime, product FROM {meta['table']} WHERE isExecuted=1")
        for r in res: r["strategy"] = strategy; rows.append(r)
    return rows

@app.get("/api/history")
def get_history():
    return db_fetchall("SELECT strategy, symbol, buy_time as buytime, buy_price as buyprice, sell_time as selltime, sell_price as sellprice, pnl, reason FROM ema_trades_live ORDER BY id DESC LIMIT 100")

def get_positions_for_strategy(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES: raise HTTPException(status_code=404)
    rows = db_fetchall(f"SELECT symbol, buy_price as buyprice, buy_time as buytime, product FROM {STRATEGIES[strategy]['table']} WHERE isExecuted=1")
    for row in rows:
        row["strategy"] = strategy
    return rows

def get_history_for_strategy(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES: raise HTTPException(status_code=404)
    table = "ema_trades_live" if strategy == "EMA" else "green_trades_live"
    try:
        return db_fetchall(
            f"SELECT %s as strategy, symbol, buy_time as buytime, buy_price as buyprice, sell_time as selltime, sell_price as sellprice, pnl, reason FROM {table} ORDER BY id DESC LIMIT 100",
            (strategy,),
        )
    except Exception:
        return []

def get_terminal(strategy: str):
    log_path = os.path.join(LOGS_DIR, f"{strategy.lower()}_terminal.log")
    if not os.path.exists(log_path): return {"lines": "No log yet."}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f: return {"lines": "".join(f.readlines()[-200:])}

def clear_terminal(strategy: str):
    log_path = os.path.join(LOGS_DIR, f"{strategy.lower()}_terminal.log")
    try:
        open(log_path, "w").close()
    except Exception:
        pass
    return {"success": True}

def start_strategy(strategy: str):
    strategy = strategy.upper(); meta = STRATEGIES[strategy]
    if not is_running(strategy):
        subprocess.Popen([sys.executable, meta["runner"]], cwd=meta["folder"], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform=="win32" else 0)
    return {"success": True}

def stop_strategy(strategy: str):
    strategy = strategy.upper(); runner = STRATEGIES[strategy]["runner"]
    for p in psutil.process_iter(["cmdline"]):
        if runner in " ".join(p.info.get("cmdline") or []): p.terminate()
    return {"success": True}

def terminate_strategy(strategy: str):
    strategy = strategy.upper(); runner = STRATEGIES[strategy]["runner"]
    for p in psutil.process_iter(["cmdline"]):
        if runner in " ".join(p.info.get("cmdline") or []):
            try:
                for child in p.children(recursive=True):
                    child.kill()
                p.kill()
            except Exception:
                p.terminate()
    return {"success": True}

@app.post("/api/setup-db")
def setup_db():
    for strategy, meta in STRATEGIES.items():
        try:
            import importlib.util as _iu
            spec = _iu.spec_from_file_location("engine_db", os.path.join(meta["folder"], "engine_db.py"))
            module = _iu.module_from_spec(spec); spec.loader.exec_module(module)
            module.setup_table()
        except: pass
    return {"success": True}

# ── Backtest Endpoints ────────────────────────────────────────────────────────
def run_ema_backtest():
    backtest_folder = os.path.join(BASE_DIR, "..", "Project_Backtest_Paper", "emaStrategy")
    runner = os.path.join(backtest_folder, "backtest_runner.py")
    subprocess.Popen([sys.executable, runner], cwd=backtest_folder, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform=="win32" else 0)
    return {"success": True}

def download_backtest_report():
    import glob
    backtest_folder = os.path.join(BASE_DIR, "..", "Project_Backtest_Paper", "emaStrategy")
    files = glob.glob(os.path.join(backtest_folder, "EMA_Backtest_*.xlsx"))
    if not files: raise HTTPException(404, "Report not found")
    latest = max(files, key=os.path.getctime)
    return FileResponse(latest, filename=os.path.basename(latest))

@app.get("/api/backtest/history")
def get_backtest_history():
    return db_fetchall("SELECT 'EMA' as strategy, symbol, buy_time as buytime, buy_price as buyprice, sell_time as selltime, sell_price as sellprice, pnl, reason FROM ema_trades_backtest ORDER BY id DESC LIMIT 100")

from strategy_routes.ema_routes import build_router as build_ema_router
from strategy_routes.green_routes import build_router as build_green_router

_strategy_route_handlers = {
    "SymbolRequest": SymbolRequest,
    "TargetUpdateRequest": TargetUpdateRequest,
    "get_symbols": get_symbols,
    "add_symbol": add_symbol,
    "update_target_price": update_target_price,
    "delete_symbol": delete_symbol,
    "reload_symbol_cache": reload_symbol_cache,
    "get_df": get_df,
    "get_positions_for_strategy": get_positions_for_strategy,
    "get_history_for_strategy": get_history_for_strategy,
    "get_terminal": get_terminal,
    "clear_terminal": clear_terminal,
    "start_strategy": start_strategy,
    "stop_strategy": stop_strategy,
    "terminate_strategy": terminate_strategy,
    "run_ema_backtest": run_ema_backtest,
    "download_backtest_report": download_backtest_report,
}

app.include_router(build_ema_router(_strategy_route_handlers))
app.include_router(build_green_router(_strategy_route_handlers))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
