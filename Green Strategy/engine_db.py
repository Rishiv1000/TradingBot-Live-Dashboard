"""
engine_db.py — GREEN Strategy (LIVE)
Creates this strategy's DB table and resets open positions.
"""
import os
import sys
import mysql.connector

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.insert(0, STRATEGY_DIR)
sys.path.insert(0, PROJECT_ROOT)

import st_config as config

STRATEGY_NAME = getattr(config, "ACTIVE_STRATEGY", "GREEN")
SYMBOLS_TABLE = getattr(config, "SYMBOLS_TABLE", "symbols_green")

def _db(database=None):
    return mysql.connector.connect(
        host=config.DB_HOST, user=config.DB_USER, password=config.DB_PASSWORD,
        **({"database": database} if database else {}),
    )

def setup_table():
    print(f"[{STRATEGY_NAME}] Setting up: {config.DB_NAME}.{SYMBOLS_TABLE}")
    conn = _db()
    conn.cursor().execute(f"CREATE DATABASE IF NOT EXISTS {config.DB_NAME}")
    conn.close()

    conn = _db(config.DB_NAME)
    cursor = conn.cursor()

    def ensure_col(table, col, col_def):
        cursor.execute(f"SHOW COLUMNS FROM {table} LIKE %s", (col,))
        if not cursor.fetchone():
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {SYMBOLS_TABLE} (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            symbol           VARCHAR(50)  UNIQUE,
            exchange         VARCHAR(20),
            instrument_token INT,
            isExecuted       TINYINT(1)   DEFAULT 0,
            buyprice         DOUBLE       DEFAULT NULL,
            buytime          DATETIME     DEFAULT NULL,
            buy_order_id     VARCHAR(100) DEFAULT NULL,
            product          VARCHAR(20)  DEFAULT 'MIS',
            mode             VARCHAR(20)  DEFAULT 'LIVE',
            strategy         VARCHAR(50)  DEFAULT '{STRATEGY_NAME}',
            last_sell_time   DATETIME     DEFAULT NULL
        )
    """)
    ensure_col(SYMBOLS_TABLE, "mode",     "VARCHAR(20) DEFAULT 'LIVE'")
    ensure_col(SYMBOLS_TABLE, "strategy", f"VARCHAR(50) DEFAULT '{STRATEGY_NAME}'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades_log (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            symbol        VARCHAR(50),
            buytime       DATETIME,
            buyprice      DOUBLE,
            selltime      DATETIME,
            sellprice     DOUBLE,
            pnl           DOUBLE,
            reason        VARCHAR(255),
            slippage      DOUBLE       DEFAULT 0,
            buy_order_id  VARCHAR(100),
            sell_order_id VARCHAR(100),
            mode          VARCHAR(20)  DEFAULT 'LIVE',
            strategy      VARCHAR(50)  DEFAULT NULL
        )
    """)
    ensure_col("trades_log", "mode",     "VARCHAR(20) DEFAULT 'LIVE'")
    ensure_col("trades_log", "strategy", "VARCHAR(50) DEFAULT NULL")

    conn.commit()
    conn.close()
    print(f"[{STRATEGY_NAME}] ✅ Table ready.")

def reset_positions():
    conn = _db(config.DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE {SYMBOLS_TABLE} SET isExecuted=0, buyprice=NULL, buytime=NULL, buy_order_id=NULL")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_table()
