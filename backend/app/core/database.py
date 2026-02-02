"""SQLite database initialization and connection management."""

import sqlite3
from pathlib import Path

from app.core.config import DATABASE_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT,
    exchange TEXT,
    sector TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ohlcv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    UNIQUE(stock_id, date)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_stock_date ON ohlcv(stock_id, date);
CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks(symbol);

CREATE TABLE IF NOT EXISTS backtests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    symbols TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    initial_capital REAL NOT NULL,
    commission_rate REAL NOT NULL DEFAULT 0.001,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    commission REAL NOT NULL DEFAULT 0.0,
    date TEXT NOT NULL,
    FOREIGN KEY (backtest_id) REFERENCES backtests(id)
);

CREATE INDEX IF NOT EXISTS idx_trades_backtest ON trades(backtest_id);

CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_id INTEGER NOT NULL UNIQUE,
    metrics_json TEXT NOT NULL,
    equity_curve_json TEXT NOT NULL,
    FOREIGN KEY (backtest_id) REFERENCES backtests(id)
);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Create and return a database connection.

    Args:
        db_path: Optional path to database file. Uses default if not provided.

    Returns:
        A sqlite3 Connection with row_factory set to Row.
    """
    path = db_path or DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_database(db_path: Path | None = None) -> None:
    """Create database tables if they do not exist.

    Args:
        db_path: Optional path to database file. Uses default if not provided.
    """
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
