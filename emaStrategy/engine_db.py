import mysql.connector
import os
import sys

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
if STRATEGY_DIR not in sys.path: sys.path.insert(0, STRATEGY_DIR)
if ROOT_DIR not in sys.path: sys.path.insert(0, ROOT_DIR)

import st_config_ema

def setup_db():
    conn = mysql.connector.connect(
        host=st_config_ema.DB_HOST,
        user=st_config_ema.DB_USER,
        password=st_config_ema.DB_PASSWORD,
        database=st_config_ema.DB_NAME
    )
    cursor = conn.cursor()
    STRATEGY_NAME           = getattr(config, "STRATEGY_NAME")
    EMA_SYMBOLS_LIVE_TBL    = getattr(config, "EMA_SYMBOLS_LIVE_TBL")
    EMA_TRADES_LIVE_TBL     = getattr(config, "EMA_TRADES_LIVE_TBL")

    print(f"[{STRATEGY_NAME}] Setting up database tables...")

    # 1. Live Symbols Table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {EMA_SYMBOLS_LIVE_TBL} (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            symbol              VARCHAR(50) UNIQUE,
            exchange            VARCHAR(20),
            instrument_token    INT,
            isExecuted          TINYINT(1)   DEFAULT 0,
            target_price        DOUBLE       DEFAULT 0,
            stoploss_price      DOUBLE       DEFAULT 0,
            trigger_buy_price   DOUBLE       DEFAULT NULL,
            buy_price           DOUBLE       DEFAULT NULL,
            buy_time            DATETIME     DEFAULT NULL,
            buy_order_id        VARCHAR(100) DEFAULT NULL,
            product             VARCHAR(20)  DEFAULT 'MIS',
            last_sell_time      DATETIME     DEFAULT NULL
        )
    """)
 

    # 2. Live Trades Log
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {EMA_TRADES_LIVE_TBL} (
            id                   INT AUTO_INCREMENT PRIMARY KEY,
            symbol               VARCHAR(50),
            trigger_buy_price   DOUBLE       DEFAULT NULL,
            buy_price            DOUBLE       DEFAULT NULL,
            buy_time             DATETIME     DEFAULT NULL,
            trigger_sell_price  DOUBLE       DEFAULT NULL,
            sell_price           DOUBLE       DEFAULT NULL,
            sell_time            DATETIME     DEFAULT NULL,
            pnl                  DOUBLE       DEFAULT 0,
            reason               VARCHAR(255),
            slippage             DOUBLE       DEFAULT 0,
            buy_order_id         VARCHAR(100),
            sell_order_id        VARCHAR(100),
            strategy             VARCHAR(50)  DEFAULT NULL
        )
    """)

    conn.commit()
    conn.close()
    print(f"[{STRATEGY_NAME}] Database setup complete for {EMA_SYMBOLS_LIVE_TBL}")

def setup_table():
    # Helper for dashboard API
    setup_db()

def reset_positions():
    conn = mysql.connector.connect(
        host=st_config_ema.DB_HOST,
        user=st_config_ema.DB_USER,
        password=st_config_ema.DB_PASSWORD,
        database=st_config_ema.DB_NAME
    )
    cursor = conn.cursor()
    EMA_SYMBOLS_LIVE_TBL = getattr(config, "EMA_SYMBOLS_LIVE_TBL")
    cursor.execute(f"UPDATE {EMA_SYMBOLS_LIVE_TBL} SET isExecuted=0, buy_price=NULL, buy_time=NULL, buy_order_id=NULL")
    conn.commit()
    conn.close()
    print(f"[{st_config_ema.STRATEGY_NAME}] Positions reset.")

if __name__ == "__main__":
    setup_db()
