"""Data Manager: download, import, store, and query stock OHLCV data."""

import csv
import io
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

from app.core.config import DATABASE_PATH
from app.core.database import get_connection, initialize_database
from app.models.schemas import StockInfo


class DataManager:
    """Manages stock data storage and retrieval via SQLite.

    Provides methods to download data from yfinance, import from CSV,
    and query stored OHLCV data.
    """

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or DATABASE_PATH
        initialize_database(self._db_path)

    def _get_conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    # ── Stock Metadata ──

    def get_or_create_stock(self, symbol: str, name: str | None = None,
                            exchange: str | None = None,
                            sector: str | None = None) -> int:
        """Return stock_id for symbol, creating the record if needed.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL").
            name: Company name.
            exchange: Exchange name.
            sector: Sector classification.

        Returns:
            The integer stock_id from the database.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id FROM stocks WHERE symbol = ?",
                (symbol.upper(),)
            ).fetchone()
            if row:
                return row["id"]

            cursor = conn.execute(
                "INSERT INTO stocks (symbol, name, exchange, sector) "
                "VALUES (?, ?, ?, ?)",
                (symbol.upper(), name, exchange, sector)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def list_stocks(self) -> list[StockInfo]:
        """Return all stored stock metadata.

        Returns:
            List of StockInfo objects.
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, symbol, name, exchange, sector FROM stocks "
                "ORDER BY symbol"
            ).fetchall()
            return [
                StockInfo(
                    id=r["id"], symbol=r["symbol"], name=r["name"],
                    exchange=r["exchange"], sector=r["sector"]
                )
                for r in rows
            ]
        finally:
            conn.close()

    def get_stock_info(self, symbol: str) -> StockInfo | None:
        """Return stock metadata for a given symbol.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            StockInfo if found, None otherwise.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, symbol, name, exchange, sector FROM stocks "
                "WHERE symbol = ?",
                (symbol.upper(),)
            ).fetchone()
            if not row:
                return None
            return StockInfo(
                id=row["id"], symbol=row["symbol"], name=row["name"],
                exchange=row["exchange"], sector=row["sector"]
            )
        finally:
            conn.close()

    # ── Data Download (yfinance) ──

    def download_stock_data(self, symbol: str,
                            start_date: str | None = None,
                            end_date: str | None = None,
                            period: str | None = "5y") -> int:
        """Download OHLCV data from yfinance and store in database.

        Args:
            symbol: Stock ticker symbol.
            start_date: Start date string (YYYY-MM-DD). If provided, period is ignored.
            end_date: End date string (YYYY-MM-DD).
            period: yfinance period string (e.g., "1y", "5y"). Used if start_date is None.

        Returns:
            Number of rows inserted/updated.

        Raises:
            ValueError: If no data is returned from yfinance.
        """
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info or {}

        stock_name = info.get("shortName") or info.get("longName")
        exchange = info.get("exchange")
        sector = info.get("sector")
        stock_id = self.get_or_create_stock(
            symbol, name=stock_name, exchange=exchange, sector=sector
        )

        if start_date:
            df = ticker.history(start=start_date, end=end_date)
        else:
            df = ticker.history(period=period)

        if df.empty:
            raise ValueError(
                f"No data returned from yfinance for symbol '{symbol}'"
            )

        return self._store_dataframe(stock_id, df)

    def _store_dataframe(self, stock_id: int, df: pd.DataFrame) -> int:
        """Store a pandas DataFrame of OHLCV data into the database.

        Args:
            stock_id: The database stock ID.
            df: DataFrame with columns Open, High, Low, Close, Volume and a DatetimeIndex.

        Returns:
            Number of rows inserted.
        """
        conn = self._get_conn()
        try:
            rows_inserted = 0
            for date_idx, row in df.iterrows():
                date_str = pd.Timestamp(date_idx).strftime("%Y-%m-%d")
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO ohlcv "
                        "(stock_id, date, open, high, low, close, volume) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            stock_id, date_str,
                            float(row["Open"]), float(row["High"]),
                            float(row["Low"]), float(row["Close"]),
                            int(row["Volume"])
                        )
                    )
                    rows_inserted += 1
                except sqlite3.IntegrityError:
                    pass
            conn.commit()
            return rows_inserted
        finally:
            conn.close()

    # ── CSV Import ──

    def import_csv(self, symbol: str, csv_content: str,
                   name: str | None = None) -> int:
        """Import OHLCV data from CSV content string.

        Expected CSV columns: date, open, high, low, close, volume
        (case-insensitive, flexible naming).

        Args:
            symbol: Stock ticker symbol.
            csv_content: Raw CSV string content.
            name: Optional company name.

        Returns:
            Number of rows imported.

        Raises:
            ValueError: If CSV format is invalid.
        """
        stock_id = self.get_or_create_stock(symbol, name=name)

        reader = csv.DictReader(io.StringIO(csv_content))
        column_map = self._build_column_map(reader.fieldnames or [])

        conn = self._get_conn()
        try:
            rows_inserted = 0
            for row in reader:
                date_str = self._parse_date(row[column_map["date"]])
                conn.execute(
                    "INSERT OR REPLACE INTO ohlcv "
                    "(stock_id, date, open, high, low, close, volume) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        stock_id, date_str,
                        float(row[column_map["open"]]),
                        float(row[column_map["high"]]),
                        float(row[column_map["low"]]),
                        float(row[column_map["close"]]),
                        int(float(row[column_map["volume"]]))
                    )
                )
                rows_inserted += 1
            conn.commit()
            return rows_inserted
        finally:
            conn.close()

    def _build_column_map(self, fieldnames: list[str]) -> dict[str, str]:
        """Map expected column names to actual CSV column names.

        Args:
            fieldnames: List of column headers from the CSV.

        Returns:
            Dictionary mapping canonical names to actual CSV column names.

        Raises:
            ValueError: If required columns are missing.
        """
        required = {"date", "open", "high", "low", "close", "volume"}
        mapping = {}
        lower_map = {f.lower().strip(): f for f in fieldnames}

        for key in required:
            if key in lower_map:
                mapping[key] = lower_map[key]
            else:
                raise ValueError(
                    f"Missing required column '{key}' in CSV. "
                    f"Found columns: {fieldnames}"
                )
        return mapping

    def _parse_date(self, date_str: str) -> str:
        """Parse various date formats into YYYY-MM-DD.

        Args:
            date_str: Date string in various formats.

        Returns:
            Normalized date string in YYYY-MM-DD format.
        """
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime(
                    "%Y-%m-%d"
                )
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: '{date_str}'")

    # ── Data Query ──

    def get_ohlcv(self, symbol: str,
                  start_date: str | None = None,
                  end_date: str | None = None) -> pd.DataFrame:
        """Query OHLCV data for a symbol within a date range.

        Args:
            symbol: Stock ticker symbol.
            start_date: Optional start date (YYYY-MM-DD), inclusive.
            end_date: Optional end date (YYYY-MM-DD), inclusive.

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.
            Index is a DatetimeIndex. Returns empty DataFrame if no data found.
        """
        conn = self._get_conn()
        try:
            query = (
                "SELECT o.date, o.open, o.high, o.low, o.close, o.volume "
                "FROM ohlcv o "
                "JOIN stocks s ON o.stock_id = s.id "
                "WHERE s.symbol = ?"
            )
            params: list = [symbol.upper()]

            if start_date:
                query += " AND o.date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND o.date <= ?"
                params.append(end_date)

            query += " ORDER BY o.date ASC"

            df = pd.read_sql_query(query, conn, params=params)
            if df.empty:
                return df

            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            return df
        finally:
            conn.close()

    def get_date_range(self, symbol: str) -> tuple[str, str] | None:
        """Return the earliest and latest dates for a symbol.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Tuple of (earliest_date, latest_date) strings, or None if no data.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT MIN(o.date) as min_date, MAX(o.date) as max_date "
                "FROM ohlcv o "
                "JOIN stocks s ON o.stock_id = s.id "
                "WHERE s.symbol = ?",
                (symbol.upper(),)
            ).fetchone()
            if row and row["min_date"]:
                return (row["min_date"], row["max_date"])
            return None
        finally:
            conn.close()

    def delete_stock_data(self, symbol: str) -> bool:
        """Delete all OHLCV data and metadata for a symbol.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            True if data was deleted, False if symbol not found.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id FROM stocks WHERE symbol = ?",
                (symbol.upper(),)
            ).fetchone()
            if not row:
                return False

            stock_id = row["id"]
            conn.execute("DELETE FROM ohlcv WHERE stock_id = ?", (stock_id,))
            conn.execute("DELETE FROM stocks WHERE id = ?", (stock_id,))
            conn.commit()
            return True
        finally:
            conn.close()
