from fastapi import APIRouter


def build_router(handlers):
    router = APIRouter(prefix="/api/ema", tags=["EMA"])

    @router.get("/symbols")
    def get_symbols():
        return handlers["get_symbols"]("EMA")

    @router.post("/symbols")
    def add_symbol(body: handlers["SymbolRequest"]):
        return handlers["add_symbol"]("EMA", body)

    @router.delete("/symbols/{symbol}")
    def delete_symbol(symbol: str):
        return handlers["delete_symbol"]("EMA", symbol)

    @router.post("/symbols/reload-cache")
    def reload_symbols():
        return handlers["reload_symbol_cache"]("EMA")

    @router.get("/df/{symbol}")
    def get_df(symbol: str):
        return handlers["get_df"]("EMA", symbol)

    @router.get("/positions")
    def get_positions():
        return handlers["get_positions_for_strategy"]("EMA")

    @router.get("/history")
    def get_history():
        return handlers["get_history_for_strategy"]("EMA")

    @router.get("/terminal")
    def get_terminal():
        return handlers["get_terminal"]("EMA")

    @router.delete("/terminal")
    def clear_terminal():
        return handlers["clear_terminal"]("EMA")

    @router.post("/start")
    def start_strategy():
        return handlers["start_strategy"]("EMA")

    @router.post("/stop")
    def stop_strategy():
        return handlers["stop_strategy"]("EMA")

    @router.post("/terminate")
    def terminate_strategy():
        return handlers["terminate_strategy"]("EMA")

    @router.post("/backtest")
    def run_backtest():
        return handlers["run_ema_backtest"]()

    @router.get("/backtest/download")
    def download_backtest_report():
        return handlers["download_backtest_report"]()

    return router
