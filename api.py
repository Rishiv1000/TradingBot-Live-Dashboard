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
    # Set defaults so the script doesn't crash immediately but shows the error
    API_KEY = API_SECRET = DB_HOST = DB_USER = DB_PASSWORD = DB_NAME = ""
    DB_POOL_SIZE = 32
    ACCESS_TOKEN_FILE = LOGS_DIR = ""

STRATEGIES = {
    "GREEN": {
        "folder": os.path.abspath(os.path.join(BASE_DIR, "Green Strategy")),
        "runner": os.path.abspath(os.path.join(BASE_DIR, "Green Strategy", "main_runner.py")),
        "table":  "green_symbols_live",
        "color":  "#2ea043",
    },
    "GREEN3": {
        "folder": os.path.abspath(os.path.join(BASE_DIR, "Green3 Strategy")),
        "runner": os.path.abspath(os.path.join(BASE_DIR, "Green3 Strategy", "main_runner.py")),
        "table":  "green3_symbols_live",
        "color":  "#58a6ff",
    },
    "EMA": {
        "folder": os.path.abspath(os.path.join(BASE_DIR, "EMA_Strategy")),
        "runner": os.path.abspath(os.path.join(BASE_DIR, "EMA_Strategy", "main_runner.py")),
        "table":  "ema_symbols_live",
        "color":  "#ff9800",
    },
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
try:
    print(f"DEBUG: DB_HOST={DB_HOST}, DB_USER={DB_USER}, DB_NAME={DB_NAME}, DB_POOL_SIZE={DB_POOL_SIZE}")
    _db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="live_pool",
        pool_size=DB_POOL_SIZE,
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    print(f"✅ Database Pool initialized with size: {DB_POOL_SIZE}")
except Exception as e:
    print(f"❌ DB TABLES ERRORS >>> PLEASE CHECK DB TABLE EITHER NOT CREATE OR OTHERS: {e}")
    # We don't exit here so we can see the error in logs, but _db() will fail later


def _db():
    if _db_pool is None:
        raise Exception("DB TABLES ERRORS >>> PLEASE CHECK DB TABLE EITHER NOT CREATE OR OTHERS")
    return _db_pool.get_connection()


def db_fetchall(query: str, params=()):
    conn = None
    try:
        conn = _db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        if conn:
            conn.close()


def db_exec(query: str, params=()):
    conn = None
    try:
        conn = _db()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
    finally:
        if conn:
            conn.close()


def db_scalar(query: str, params=()):
    try:
        conn = _db()
    except mysql.connector.errors.PoolError:
        raise HTTPException(status_code=503, detail="Database pool exhausted — try again shortly")
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        r = cursor.fetchone()
        return r[0] if r else 0
    finally:
        conn.close()


# ── Kite helpers ──────────────────────────────────────────────────────────────
def get_kite():
    """Return a KiteConnect instance with access token set, or None."""
    if not API_KEY:
        return None
    if not os.path.exists(ACCESS_TOKEN_FILE):
        return None
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=API_KEY, timeout=10)
        with open(ACCESS_TOKEN_FILE) as f:
            tok = f.read().strip()
        if not tok:
            return None
        kite.set_access_token(tok)
        return kite
    except Exception as e:
        print(f"[get_kite] error: {e}")
        return None


def kite_logged_in() -> bool:
    """Verify the access token is valid by fetching profile from Zerodha."""
    kite = get_kite()
    if not kite:
        return False
    try:
        kite.profile()
        return True
    except Exception:
        return False


# ── Process helpers ───────────────────────────────────────────────────────────

_proc_cache: dict = {}
_proc_cache_ts: float = 0.0
_PROC_CACHE_TTL = 2.0


def _scan_all_procs() -> dict:
    runner_map = {
        os.path.normcase(os.path.abspath(meta["runner"])): name
        for name, meta in STRATEGIES.items()
    }
    found: dict = {name: None for name in STRATEGIES}
    for p in psutil.process_iter(["pid", "cmdline", "status"]):
        try:
            if p.info["status"] == psutil.STATUS_ZOMBIE:
                continue
            cmd = os.path.normcase(" ".join(p.info.get("cmdline") or []))
            for norm_runner, name in runner_map.items():
                if norm_runner in cmd:
                    found[name] = p
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return found


def _get_proc_cache() -> dict:
    global _proc_cache, _proc_cache_ts
    now = _time.monotonic()
    if now - _proc_cache_ts > _PROC_CACHE_TTL:
        _proc_cache    = _scan_all_procs()
        _proc_cache_ts = now
    return _proc_cache


def _find_proc(runner: str):
    norm = os.path.normcase(os.path.abspath(runner))
    cache = _get_proc_cache()
    for name, meta in STRATEGIES.items():
        if os.path.normcase(os.path.abspath(meta["runner"])) == norm:
            return cache.get(name)
    return None


def _invalidate_proc_cache():
    global _proc_cache_ts
    _proc_cache_ts = 0.0


def is_running(strategy: str) -> bool:
    p = _get_proc_cache().get(strategy)
    return p is not None


# ── Pydantic models ───────────────────────────────────────────────────────────
class SessionRequest(BaseModel):
    request_token: str


class SymbolRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    target_price: float = 0.0

class TargetUpdateRequest(BaseModel):
    symbol: str
    target_price: float

class PoolResizeRequest(BaseModel):
    new_size: int


# ═════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/db/status")
def get_db_status():
    try:
        conn = _db()
        cursor = conn.cursor(dictionary=True)
        # Query MySQL for global thread info
        cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
        connected = cursor.fetchone()["Value"]
        cursor.execute("SHOW STATUS LIKE 'Threads_running'")
        running = cursor.fetchone()["Value"]
        conn.close()
        return {
            "pool_name": _db_pool.pool_name,
            "pool_size": _db_pool.pool_size,
            "threads_connected": connected,
            "threads_running": running,
            "db_name": DB_NAME
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/db/resize")
def resize_pool(body: PoolResizeRequest):
    global _db_pool, DB_POOL_SIZE
    if body.new_size < 5 or body.new_size > 200:
        raise HTTPException(status_code=400, detail="Size must be between 5 and 200")
    
    # Update base_config.py
    try:
        base_cfg_path = os.path.join(BASE_DIR, "config", "base_config.py")
        with open(base_cfg_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(base_cfg_path, "w", encoding="utf-8") as f:
            found = False
            for line in lines:
                if line.strip().startswith("DB_POOL_SIZE ="):
                    f.write(f"DB_POOL_SIZE = {body.new_size}\n")
                    found = True
                else:
                    f.write(line)
            if not found:
                # If not found, append it to DATABASE CONFIG section or end
                f.write(f"\nDB_POOL_SIZE = {body.new_size}\n")
        
        DB_POOL_SIZE = body.new_size
        return {"success": True, "message": f"Pool size updated to {body.new_size} in base_config.py. Restart recommended."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _read_trading_enabled() -> bool:
    """Read REAL_TRADING_ENABLED from base_config.py by parsing the file directly."""
    try:
        base_cfg_path = os.path.join(BASE_DIR, "config", "base_config.py")
        with open(base_cfg_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("REAL_TRADING_ENABLED"):
                    # e.g.  REAL_TRADING_ENABLED = True
                    val = line.split("=", 1)[-1].strip()
                    return val.lower() in ("true", "1", "yes")
    except Exception:
        pass
    return False


@app.post("/api/shutdown_system")
def shutdown_system():
    print("[!] Shutdown triggered via API.")
    with open(".stop_backend", "w") as f:
        f.write("stop")
    for strategy in STRATEGIES:
        try:
            from api import stop_strategy
            stop_strategy(strategy)
        except:
            pass
    import os, signal
    os.kill(os.getpid(), signal.SIGINT)
    return {"success": True, "message": "System is shutting down..."}

@app.get("/api/status")
def get_status():
    trading_enabled = _read_trading_enabled()

    cache = _get_proc_cache()
    result = {}
    for strategy, meta in STRATEGIES.items():
        running    = cache.get(strategy) is not None
        sym_count  = 0
        open_count = 0
        try:
            conn = _db()
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {meta['table']}")
            sym_count = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM {meta['table']} WHERE isExecuted=1")
            open_count = cur.fetchone()[0]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[status] DB error for {strategy}: {e}")
        result[strategy] = {
            "running":         running,
            "symbol_count":    sym_count,
            "open_count":      open_count,
            "color":           meta["color"],
            "trading_enabled": trading_enabled,
        }
    return result


@app.get("/api/kite/status")
def kite_status():
    return {"logged_in": kite_logged_in()}


@app.get("/api/kite/login_url")
def kite_login_url():
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not configured")
    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=API_KEY)
    return {"url": kite.login_url()}


@app.post("/api/kite/session")
def kite_session(body: SessionRequest):
    if not API_KEY or not API_SECRET:
        return {"success": False, "error": "API_KEY or API_SECRET not configured"}
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=API_KEY)
        data = kite.generate_session(body.request_token, api_secret=API_SECRET)
        with open(ACCESS_TOKEN_FILE, "w") as f:
            f.write(data["access_token"])
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/symbols/{strategy}")
def get_symbols(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    try:
        return db_fetchall(
            f"SELECT symbol, exchange, instrument_token, isExecuted, target_price FROM {STRATEGIES[strategy]['table']} ORDER BY symbol"
        )
    except Exception:
        return []


@app.post("/api/symbols/{strategy}")
def add_symbol(strategy: str, body: SymbolRequest):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    kite = get_kite()
    if kite is None:
        raise HTTPException(status_code=401, detail="Kite session missing — login first")
    try:
        inst = f"{body.exchange.upper()}:{body.symbol.upper()}"
        ltp_data = kite.ltp(inst)
        token = ltp_data[inst]["instrument_token"]
        table = STRATEGIES[strategy]["table"]
        db_exec(
            f"INSERT INTO {table} (symbol, exchange, instrument_token, isExecuted, target_price) VALUES (%s, %s, %s, 0, %s) "
            f"ON DUPLICATE KEY UPDATE exchange=%s, instrument_token=%s, target_price=%s",
            (body.symbol.upper(), body.exchange.upper(), token, body.target_price, body.exchange.upper(), token, body.target_price),
        )
        return {"success": True, "token": token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/symbols/{strategy}/target")
def update_target_price(strategy: str, body: TargetUpdateRequest):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    table = STRATEGIES[strategy]["table"]
    db_exec(
        f"UPDATE {table} SET target_price=%s WHERE symbol=%s",
        (body.target_price, body.symbol.upper()),
    )
    return {"success": True}


@app.delete("/api/symbols/{strategy}/{symbol}")
def delete_symbol(strategy: str, symbol: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    db_exec(
        f"DELETE FROM {STRATEGIES[strategy]['table']} WHERE symbol=%s",
        (symbol.upper(),),
    )
    return {"success": True}


@app.get("/api/df/{strategy}/{symbol}")
def get_df(strategy: str, symbol: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    meta = STRATEGIES[strategy]
    cache_path = os.path.join(meta["folder"], "live_df_cache.pkl")
    if not os.path.exists(cache_path):
        return {"candle_count": 0, "last_candle": None, "columns": [], "data": []}
    try:
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
        if symbol.upper() not in cache:
            return {"candle_count": 0, "last_candle": None, "columns": [], "data": []}
        df = cache[symbol.upper()]
        candle_count = len(df)
        last_candle = None
        if not df.empty and "date" in df.columns:
            last_candle = str(df.iloc[-1]["date"])
        df_tail = df.tail(500).fillna("")
        return {
            "candle_count": candle_count,
            "last_candle":  last_candle,
            "columns":      list(df_tail.columns),
            "data":         df_tail.to_dict(orient="records"),
        }
    except Exception as e:
        return {"candle_count": 0, "last_candle": None, "columns": [], "data": [], "error": str(e)}


@app.get("/api/positions")
def get_positions():
    rows = []
    for strategy, meta in STRATEGIES.items():
        try:
            strategy_rows = db_fetchall(
                f"SELECT symbol, buyprice, buytime, product FROM {meta['table']} WHERE isExecuted=1"
            )
            for r in strategy_rows:
                r["strategy"] = strategy
            rows.extend(strategy_rows)
        except Exception:
            pass
    return rows


@app.get("/api/history")
def get_history():
    try:
        rows = db_fetchall(
            "SELECT strategy, symbol, buytime, buyprice, selltime, sellprice, pnl, reason "
            "FROM trades_log ORDER BY id DESC LIMIT 200"
        )
        return rows
    except Exception:
        return []


@app.get("/api/terminal/{strategy}")
def get_terminal(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    log_path = os.path.join(LOGS_DIR, f"{strategy.lower()}_terminal.log")
    if not os.path.exists(log_path):
        return {"lines": "No log yet. Start the strategy first."}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"lines": "".join(lines[-200:]) or "Log is empty."}
    except Exception as e:
        return {"lines": f"Error reading log: {e}"}


@app.delete("/api/terminal/{strategy}")
def clear_terminal(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    log_path = os.path.join(LOGS_DIR, f"{strategy.lower()}_terminal.log")
    try:
        open(log_path, "w").close()
    except Exception:
        pass
    return {"success": True}
@app.get("/api/logs/backend")
def get_backend_logs():
    log_path = os.path.join(LOGS_DIR, "api.log")
    if not os.path.exists(log_path): return {"lines": "No backend log found."}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"lines": "".join(lines[-200:]) or "Log is empty."}
    except Exception as e: return {"lines": f"Error: {e}"}

@app.get("/api/logs/frontend")
def get_frontend_logs():
    log_path = os.path.join(LOGS_DIR, "vite.log")
    if not os.path.exists(log_path): return {"lines": "No frontend log found."}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"lines": "".join(lines[-200:]) or "Log is empty."}
    except Exception as e: return {"lines": f"Error: {e}"}



@app.post("/api/strategy/{strategy}/start")
def start_strategy(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    meta = STRATEGIES[strategy]
    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)

    if is_running(strategy):
        return {"success": True, "message": "Already running"}
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [sys.executable, meta["runner"]],
        cwd=meta["folder"],
        **kwargs,
    )
    _invalidate_proc_cache()
    return {"success": True}


@app.post("/api/strategy/{strategy}/stop")
def stop_strategy(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    p = _find_proc(STRATEGIES[strategy]["runner"])
    if p:
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _invalidate_proc_cache()
    return {"success": True}


@app.post("/api/strategy/{strategy}/terminate")
def terminate_strategy(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    p = _find_proc(STRATEGIES[strategy]["runner"])
    if p:
        try:
            for c in p.children(recursive=True):
                c.kill()
            p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _invalidate_proc_cache()
    return {"success": True}


@app.post("/api/strategy/stop-all")
def stop_all():
    for strategy in STRATEGIES:
        p = _find_proc(STRATEGIES[strategy]["runner"])
        if p:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    _invalidate_proc_cache()
    return {"success": True}


@app.post("/api/strategy/kill-all")
def kill_all():
    for strategy in STRATEGIES:
        p = _find_proc(STRATEGIES[strategy]["runner"])
        if p:
            try:
                for c in p.children(recursive=True):
                    c.kill()
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    _invalidate_proc_cache()
    return {"success": True}


def load_strategy_module(folder, module_name):
    import importlib.util as _iu
    file_path = os.path.join(folder, f"{module_name}.py")
    if not os.path.exists(file_path):
        raise ImportError(f"File not found: {file_path}")
    
    # Clean sys.path to avoid picking up 'config' from other projects
    project_root = os.path.dirname(folder)
    for p in list(sys.path):
        if "Project_" in p:
            sys.path.remove(p)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if folder not in sys.path:
        sys.path.insert(0, folder)

    sys.modules.pop(module_name, None)
    sys.modules.pop("st_config", None)
    sys.modules.pop("config", None)
    # Clear submodules of the shared 'config' package
    for m in list(sys.modules.keys()):
        if m.startswith("config."):
            sys.modules.pop(m, None)
    
    spec = _iu.spec_from_file_location(module_name, file_path)
    module = _iu.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

@app.post("/api/setup-db")
def setup_db():
    """Create DB tables for all strategies — each strategy sets up its own table."""
    import importlib as _il
    errors = []
    for strategy, meta in STRATEGIES.items():
        try:
            engine_db = load_strategy_module(meta["folder"], "engine_db")
            engine_db.setup_table()
        except Exception as e:
            errors.append(f"{strategy}: {e}")
    if errors:
        return {"success": False, "error": "; ".join(errors)}
    return {"success": True, "message": "All strategy tables ready."}


@app.post("/api/reset-positions")
def reset_positions():
    """Reset open positions for all strategies (clean live trade data)."""
    import importlib as _il
    errors = []
    for strategy, meta in STRATEGIES.items():
        try:
            engine_db = load_strategy_module(meta["folder"], "engine_db")
            engine_db.reset_positions()
        except Exception as e:
            errors.append(f"{strategy}: {e}")
    if errors:
        return {"success": False, "error": "; ".join(errors)}
    return {"success": True, "message": "All positions reset."}


@app.post("/api/symbols/{strategy}/bulk")
async def bulk_symbols(strategy: str, request: Request):
    """Bulk add symbols from JSON list: [{symbol, exchange}]"""
    from fastapi import Request
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    body = await request.json()
    symbols = body.get("symbols", [])
    kite = get_kite()
    if not kite:
        raise HTTPException(status_code=401, detail="Kite session missing — login first")
    added, failed = [], []
    for item in symbols:
        sym = item.get("symbol", "").strip().upper()
        exch = item.get("exchange", "NSE").strip().upper()
        if not sym:
            continue
        try:
            inst = f"{exch}:{sym}"
            token = kite.ltp(inst)[inst]["instrument_token"]
            table = STRATEGIES[strategy]["table"]
            db_exec(
                f"INSERT INTO {table} (symbol, exchange, instrument_token, isExecuted) VALUES (%s, %s, %s, 0) "
                f"ON DUPLICATE KEY UPDATE exchange=%s, instrument_token=%s",
                (sym, exch, token, exch, token),
            )
            added.append(sym)
        except Exception as e:
            failed.append({"symbol": sym, "error": str(e)})
        import time as _t; _t.sleep(0.35)  # rate limit
    return {"success": True, "added": added, "failed": failed}
def reload_symbol_cache(strategy: str):
    """Signal the strategy process to reload symbols from DB on next cycle."""
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    signal_file = os.path.join(STRATEGIES[strategy]["folder"], ".reload_symbols")
    try:
        open(signal_file, "w").close()
        return {"success": True, "message": f"{strategy} will reload symbols on next cycle."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/symbols/reload-all")
def reload_all_symbol_caches():
    """Signal all strategy processes to reload symbols."""
    for strategy, meta in STRATEGIES.items():
        signal_file = os.path.join(meta["folder"], ".reload_symbols")
        try:
            open(signal_file, "w").close()
        except Exception:
            pass
    return {"success": True, "message": "All strategies will reload symbols on next cycle."}


@app.post("/api/kite/logout")
def kite_logout():
    """Kill all strategies and clear the access token."""
    # Kill all running strategies first
    for strategy in STRATEGIES:
        p = _find_proc(STRATEGIES[strategy]["runner"])
        if p:
            try:
                for c in p.children(recursive=True):
                    c.kill()
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    _invalidate_proc_cache()
    # Clear the access token
    try:
        with open(ACCESS_TOKEN_FILE, "w") as f:
            f.write("")
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": True}


@app.post("/api/server/stop")
def stop_server():
    """Gracefully stop the API server."""
    import threading
    def _shutdown():
        import time as _t
        _t.sleep(0.5)
        os._exit(0)
    threading.Thread(target=_shutdown, daemon=True).start()
    return {"success": True, "message": "Server shutting down..."}
