import os
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api_shared import (
    API_KEY, API_SECRET, DB_NAME, ACCESS_TOKEN, 
    STRATEGIES, _db, db_fetchall, db_exec, _get_proc_cache,
    SessionRequest, TradingConfigRequest, TargetUpdateRequest,
    get_all_relevant_processes, kill_process_by_pid
)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="MultiStrategy Live API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Endpoints ──────────────────────────────────────────────────────────
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
    from dotenv import dotenv_values
    cache    = _get_proc_cache()
    # Check both configuration/.env and root .env for robustness
    paths = [
        os.path.join(BASE_DIR, "configuration", ".env"),
        os.path.join(BASE_DIR, ".env")
    ]
    env_vars = {}
    for p in paths:
        if os.path.exists(p):
            env_vars.update(dotenv_values(p))
            
    val = str(env_vars.get("REAL_TRADING_ENABLED", "False")).strip().lower()
    real_trading = val == "true"
    result = {}
    for strategy, meta in STRATEGIES.items():
        sym_count = open_count = 0
        conn = None
        try:
            conn = _db()
            cur  = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {meta['table']}")
            sym_count  = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM {meta['table']} WHERE isExecuted=1")
            open_count = cur.fetchone()[0]
        except Exception:
            pass
        finally:
            if conn: conn.close()
        result[strategy] = {
            "running":         cache.get(strategy) is not None,
            "symbol_count":    sym_count,
            "open_count":      open_count,
            "trading_enabled": real_trading,
            "color":           meta.get("color", "#58a6ff"),
        }
    return result



@app.get("/api/kite/status")
def get_kite_status():
    if not API_KEY: return {"logged_in": False, "error": "API_KEY missing"}
    if not ACCESS_TOKEN: return {"logged_in": False, "info": "No access token"}
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=API_KEY)
        kite.set_access_token(ACCESS_TOKEN)
        profile = kite.profile()
        return {"logged_in": True, "user_id": profile.get("user_id"), "user_name": profile.get("user_name")}
    except Exception as e: return {"logged_in": False, "error": str(e)}

@app.post("/api/kite/session")
def kite_session(body: SessionRequest):
    if not API_KEY or not API_SECRET:
        return {"success": False, "error": "API_KEY/API_SECRET missing"}
    try:
        from kiteconnect import KiteConnect
        from dotenv import set_key
        kite = KiteConnect(api_key=API_KEY)
        data = kite.generate_session(body.request_token, api_secret=API_SECRET)
        token = data["access_token"]
        env_path = os.path.join(BASE_DIR, "configuration", ".env")
        set_key(env_path, "KITE_ACCESS_TOKEN", token)
        return {"success": True}
    except Exception as e: return {"success": False, "error": str(e)}

@app.get("/api/logs/backend")
def get_backend_log():
    log_path = os.path.join(BASE_DIR, "others", "logs", "api.log")
    if not os.path.exists(log_path): return {"lines": "No log yet."}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        return {"lines": "".join(f.readlines()[-300:])}

@app.get("/api/logs/frontend")
def get_frontend_log():
    log_path = os.path.join(BASE_DIR, "others", "logs", "vite.log")
    if not os.path.exists(log_path): return {"lines": "No log yet."}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        return {"lines": "".join(f.readlines()[-300:])}

@app.post("/api/setup-db")
def setup_db():
    try:
        from emaStrategy.engine_db import setup_db as ema_setup
        from greenStrategy.engine_db import setup_table as green_setup
        ema_setup()
        green_setup()
        return {"success": True, "message": "Database tables created successfully."}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/set-defaults")
def set_defaults():
    try:
        from emaStrategy.engine_db import reset_positions as ema_reset
        from greenStrategy.engine_db import reset_positions as green_reset
        ema_reset()
        green_reset()
        return {"success": True, "message": "Positions reset successfully."}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/system/real-trading")
def set_real_trading(body: TradingConfigRequest):
    try:
        from dotenv import set_key
        env_path = os.path.join(BASE_DIR, "configuration", ".env")
        val = "True" if body.real_trading_enabled else "False"
        set_key(env_path, "REAL_TRADING_ENABLED", val)
        return {"success": True, "enabled": body.real_trading_enabled}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/system/processes")
def list_processes():
    return get_all_relevant_processes()

class KillRequest(BaseModel):
    pid: int

@app.post("/api/system/kill")
def kill_system_process(body: KillRequest):
    success = kill_process_by_pid(body.pid)
    return {"success": success}

# ── Include Strategy Routers ──────────────────────────────────────────────────
from emaStrategy.endpoints_ema import router as ema_router
from greenStrategy.endpoints_green import router as green_router

app.include_router(ema_router)
app.include_router(green_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
