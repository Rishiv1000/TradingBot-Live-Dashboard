import os
import pickle
import subprocess
import sys
import time as _time
from typing import Optional

import mysql.connector
import mysql.connector.pooling
import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


try:
    from config.base_config import (
        API_KEY, API_SECRET, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_POOL_SIZE,
        ACCESS_TOKEN_FILE, LOGS_DIR
    )
    print("✅ Configuration loaded successfully.")
except Exception as e:
    print(f"❌ ERROR: Failed to load configuration from base_config.py: {e}")
    API_KEY = API_SECRET = DB_HOST = DB_USER = DB_PASSWORD = DB_NAME = ""
    DB_POOL_SIZE = 32
    ACCESS_TOKEN_FILE = LOGS_DIR = ""

STRATEGIES = {
     "EMA": {
        "folder": os.path.abspath(os.path.join(BASE_DIR, "EMA_Strategy")),
        "runner": os.path.abspath(os.path.join(BASE_DIR, "EMA_Strategy", "main_runner.py")),
        "table":  "ema_symbols_live",
        "color":  "#ff9800",
    },
    # "GREEN": {
    #     "folder": os.path.abspath(os.path.join(BASE_DIR, "Green Strategy")),
    #     "runner": os.path.abspath(os.path.join(BASE_DIR, "Green Strategy", "main_runner.py")),
    #     "table":  "green_symbols_live",
    #     "color":  "#2ea043",
    # },
}

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="MultiStrategy Live API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB connection pool ────────────────────────────────────────────────────────
_db_pool = None
_db_error_msg = ""
try:
    _db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="live_pool",
        pool_size=DB_POOL_SIZE,
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    print(f"✅ Database Pool initialized.")
except Exception as e:
    _db_error_msg = str(e)
    print(f"❌ DB Pool Error: {_db_error_msg}")


def _db():
    if _db_pool is None:
        raise Exception(f"DB Error: {_db_error_msg}")
    return _db_pool.get_connection()


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
class PoolResizeRequest(BaseModel): new_size: int

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/api/db/status")
def get_db_status():
    try:
        conn = _db(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW STATUS LIKE 'Threads_connected'"); connected = cursor.fetchone()["Value"]
        cursor.execute("SHOW STATUS LIKE 'Threads_running'"); running = cursor.fetchone()["Value"]
        conn.close()
        return {"pool_name": _db_pool.pool_name, "pool_size": _db_pool.pool_size, "threads_connected": connected, "threads_running": running, "db_name": DB_NAME}
    except Exception as e: return {"error": str(e)}

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
        result[strategy] = {"running": cache.get(strategy) is not None, "symbol_count": sym_count, "open_count": open_count, "color": meta["color"]}
    return result

@app.get("/api/kite/status")
def kite_status(): return {"logged_in": kite_logged_in()}

@app.post("/api/kite/session")
def kite_session(body: SessionRequest):
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=API_KEY)
        data = kite.generate_session(body.request_token, api_secret=API_SECRET)
        with open(ACCESS_TOKEN_FILE, "w") as f: f.write(data["access_token"])
        return {"success": True}
    except Exception as e: return {"success": False, "error": str(e)}

@app.get("/api/symbols/{strategy}")
def get_symbols(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES: raise HTTPException(status_code=404)
    return db_fetchall(f"SELECT symbol, exchange, instrument_token, isExecuted, target_price FROM {STRATEGIES[strategy]['table']} ORDER BY symbol")

@app.post("/api/symbols/{strategy}")
def add_symbol(strategy: str, body: SymbolRequest):
    strategy = strategy.upper(); kite = get_kite()
    if not kite: raise HTTPException(status_code=401)
    inst = f"{body.exchange.upper()}:{body.symbol.upper()}"
    token = kite.ltp(inst)[inst]["instrument_token"]
    table = STRATEGIES[strategy]["table"]
    db_exec(f"INSERT INTO {table} (symbol, exchange, instrument_token, isExecuted, target_price) VALUES (%s, %s, %s, 0, %s) ON DUPLICATE KEY UPDATE target_price=%s",
            (body.symbol.upper(), body.exchange.upper(), token, body.target_price, body.target_price))
    return {"success": True}

@app.delete("/api/symbols/{strategy}/{symbol}")
def delete_symbol(strategy: str, symbol: str):
    db_exec(f"DELETE FROM {STRATEGIES[strategy.upper()]['table']} WHERE symbol=%s", (symbol.upper(),))
    return {"success": True}

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

@app.get("/api/terminal/{strategy}")
def get_terminal(strategy: str):
    log_path = os.path.join(LOGS_DIR, f"{strategy.lower()}_terminal.log")
    if not os.path.exists(log_path): return {"lines": "No log yet."}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f: return {"lines": "".join(f.readlines()[-200:])}

@app.post("/api/strategy/{strategy}/start")
def start_strategy(strategy: str):
    strategy = strategy.upper(); meta = STRATEGIES[strategy]
    if not is_running(strategy):
        subprocess.Popen([sys.executable, meta["runner"]], cwd=meta["folder"], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform=="win32" else 0)
    return {"success": True}

@app.post("/api/strategy/{strategy}/stop")
def stop_strategy(strategy: str):
    strategy = strategy.upper(); runner = STRATEGIES[strategy]["runner"]
    for p in psutil.process_iter(["cmdline"]):
        if runner in " ".join(p.info.get("cmdline") or []): p.terminate()
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
@app.post("/api/strategy/EMA/backtest")
def run_ema_backtest():
    backtest_folder = os.path.join(BASE_DIR, "..", "Project_Backtest_Paper", "EMA_Strategy")
    runner = os.path.join(backtest_folder, "backtest_runner.py")
    subprocess.Popen([sys.executable, runner], cwd=backtest_folder, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform=="win32" else 0)
    return {"success": True}

@app.get("/api/strategy/EMA/backtest/download")
def download_backtest_report():
    import glob
    backtest_folder = os.path.join(BASE_DIR, "..", "Project_Backtest_Paper", "EMA_Strategy")
    files = glob.glob(os.path.join(backtest_folder, "EMA_Backtest_*.xlsx"))
    if not files: raise HTTPException(404, "Report not found")
    latest = max(files, key=os.path.getctime)
    return FileResponse(latest, filename=os.path.basename(latest))

@app.get("/api/backtest/history")
def get_backtest_history():
    return db_fetchall("SELECT 'EMA' as strategy, symbol, buy_time as buytime, buy_price as buyprice, sell_time as selltime, sell_price as sellprice, pnl, reason FROM ema_trades_backtest ORDER BY id DESC LIMIT 100")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
