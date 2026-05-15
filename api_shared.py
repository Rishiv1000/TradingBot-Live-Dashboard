import os
import sys
import time as _time
import pickle
import subprocess
import mysql.connector
import psutil
from fastapi import HTTPException
from pydantic import BaseModel

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from configuration.base_config import (
        API_KEY, API_SECRET, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME,
        ACCESS_TOKEN, LOGS_DIR, BACKTEST_RESULTS_DIR, REAL_TRADING_ENABLED
    )
except Exception as e:
    print(f"❌ Shared API: Configuration error: {e}")
    API_KEY = API_SECRET = DB_HOST = DB_USER = DB_PASSWORD = DB_NAME = ""
    ACCESS_TOKEN = LOGS_DIR = BACKTEST_RESULTS_DIR = ""
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

# ── DB Helpers ────────────────────────────────────────────────────────────────
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

# ── Process Helpers ───────────────────────────────────────────────────────────
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

def start_strategy_process(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES: return {"success": False, "error": "Unknown strategy"}
    meta = STRATEGIES[strategy]
    if not is_running(strategy):
        subprocess.Popen([sys.executable, meta["runner"]], cwd=meta["folder"], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform=="win32" else 0)
    return {"success": True}

def stop_strategy_process(strategy: str):
    strategy = strategy.upper()
    proc = _get_proc_cache().get(strategy)
    if proc:
        try:
            proc.terminate()
            return {"success": True}
        except:
            return {"success": False, "error": "Terminate failed"}
    return {"success": True, "info": "Already stopped"}

def terminate_strategy_process(strategy: str):
    strategy = strategy.upper()
    proc = _get_proc_cache().get(strategy)
    if proc:
        try:
            proc.kill()
            return {"success": True}
        except:
            return {"success": False, "error": "Kill failed"}
    return {"success": True, "info": "No process found"}

# ── Shared Models ─────────────────────────────────────────────────────────────
class SessionRequest(BaseModel):
    request_token: str

class SymbolRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    target_price: float = 0.0

class TargetUpdateRequest(BaseModel):
    symbol: str
    target_price: float

class TradingConfigRequest(BaseModel):
    real_trading_enabled: bool
