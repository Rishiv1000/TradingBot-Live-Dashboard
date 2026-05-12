"""
terminal_capture.py — Redirects stdout/stderr to a log file per strategy.
Used by main_runner.py to capture terminal output for the dashboard.
"""
import os
import sys

# Logs directory — one level up from config/
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

_original_stdout = sys.stdout
_original_stderr = sys.stderr
_log_file = None


def start_strategy_capture(strategy_name: str):
    """Redirect stdout/stderr to logs/<strategy_name>_terminal.log"""
    global _log_file
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_path = os.path.join(LOGS_DIR, f"{strategy_name.lower()}_terminal.log")
    try:
        _log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        sys.stdout = _log_file
        sys.stderr = _log_file
    except Exception as e:
        print(f"[terminal_capture] Could not open log file: {e}", file=_original_stderr)


def stop_strategy_capture(strategy_name: str):
    """Restore stdout/stderr and close the log file."""
    global _log_file
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    if _log_file:
        try:
            _log_file.close()
        except Exception:
            pass
        _log_file = None
