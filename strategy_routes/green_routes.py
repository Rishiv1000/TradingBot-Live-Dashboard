from fastapi import APIRouter


def build_router(handlers):
    router = APIRouter(prefix="/api/green", tags=["GREEN"])

    @router.get("/symbols")
    def get_symbols():
        return handlers["get_symbols"]("GREEN")

    @router.post("/symbols")
    def add_symbol(body: handlers["SymbolRequest"]):
        return handlers["add_symbol"]("GREEN", body)

    @router.delete("/symbols/{symbol}")
    def delete_symbol(symbol: str):
        return handlers["delete_symbol"]("GREEN", symbol)

    @router.post("/symbols/reload-cache")
    def reload_symbols():
        return handlers["reload_symbol_cache"]("GREEN")

    @router.get("/df/{symbol}")
    def get_df(symbol: str):
        return handlers["get_df"]("GREEN", symbol)

    @router.get("/positions")
    def get_positions():
        return handlers["get_positions_for_strategy"]("GREEN")

    @router.get("/history")
    def get_history():
        return handlers["get_history_for_strategy"]("GREEN")

    @router.get("/terminal")
    def get_terminal():
        return handlers["get_terminal"]("GREEN")

    @router.delete("/terminal")
    def clear_terminal():
        return handlers["clear_terminal"]("GREEN")

    @router.post("/start")
    def start_strategy():
        return handlers["start_strategy"]("GREEN")

    @router.post("/stop")
    def stop_strategy():
        return handlers["stop_strategy"]("GREEN")

    @router.post("/backtest")
    def run_backtest():
        return {"success": False, "error": "GREEN backtest is not configured in live project yet."}

    return router
