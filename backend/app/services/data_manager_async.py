"""Async Data Manager: download, import, store, and query stock OHLCV data.

This is the async SQLAlchemy version that replaces the sync sqlite3 implementation.
"""

import csv
import io
from datetime import datetime

import pandas as pd
import yfinance as yf
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OHLCV, Stock
from app.models.schemas import StockInfo


class DataManager:
    """Async data manager for stock OHLCV data using SQLAlchemy.

    Provides methods to download data from yfinance, import from CSV,
    and query stored OHLCV data.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize with async database session.

        Args:
            db_session: SQLAlchemy async session.
        """
        self.db = db_session

    # ── Stock Metadata ──

    async def get_or_create_stock(
        self,
        symbol: str,
        name: str | None = None,
        exchange: str | None = None,
        sector: str | None = None,
    ) -> int:
        """Return stock_id for symbol, creating the record if needed.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL").
            name: Company name.
            exchange: Exchange name.
            sector: Sector classification.

        Returns:
            The integer stock_id from the database.
        """
        symbol_upper = symbol.upper()

        # Try to find existing stock
        result = await self.db.execute(select(Stock).where(Stock.symbol == symbol_upper))
        stock = result.scalar_one_or_none()

        if stock:
            return stock.id

        # Create new stock
        new_stock = Stock(symbol=symbol_upper, name=name, exchange=exchange, sector=sector)
        self.db.add(new_stock)
        await self.db.flush()  # Flush to get the ID
        return new_stock.id

    async def list_stocks(self) -> list[StockInfo]:
        """Return all stored stock metadata.

        Returns:
            List of StockInfo objects.
        """
        result = await self.db.execute(
            select(Stock).order_by(Stock.symbol)
        )
        stocks = result.scalars().all()

        return [
            StockInfo(
                id=s.id,
                symbol=s.symbol,
                name=s.name,
                exchange=s.exchange,
                sector=s.sector,
            )
            for s in stocks
        ]

    async def get_stock_info(self, symbol: str) -> StockInfo | None:
        """Return stock metadata for a given symbol.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            StockInfo if found, None otherwise.
        """
        result = await self.db.execute(select(Stock).where(Stock.symbol == symbol.upper()))
        stock = result.scalar_one_or_none()

        if not stock:
            return None

        return StockInfo(
            id=stock.id,
            symbol=stock.symbol,
            name=stock.name,
            exchange=stock.exchange,
            sector=stock.sector,
        )

    # ── Data Download (yfinance) ──

    async def download_stock_data(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str | None = "5y",
    ) -> int:
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
        stock_id = await self.get_or_create_stock(
            symbol, name=stock_name, exchange=exchange, sector=sector
        )

        if start_date:
            df = ticker.history(start=start_date, end=end_date)
        else:
            df = ticker.history(period=period)

        if df.empty:
            raise ValueError(f"No data returned from yfinance for symbol '{symbol}'")

        return await self._store_dataframe(stock_id, df)

    async def _store_dataframe(self, stock_id: int, df: pd.DataFrame) -> int:
        """Store a pandas DataFrame of OHLCV data into the database.

        Args:
            stock_id: The database stock ID.
            df: DataFrame with columns Open, High, Low, Close, Volume and a DatetimeIndex.

        Returns:
            Number of rows inserted.
        """
        rows_inserted = 0

        for date_idx, row in df.iterrows():
            date_str = pd.Timestamp(date_idx).strftime("%Y-%m-%d")

            # Check if record exists
            result = await self.db.execute(
                select(OHLCV).where(OHLCV.stock_id == stock_id, OHLCV.date == date_str)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.open = float(row["Open"])
                existing.high = float(row["High"])
                existing.low = float(row["Low"])
                existing.close = float(row["Close"])
                existing.volume = int(row["Volume"])
            else:
                # Insert new record
                new_ohlcv = OHLCV(
                    stock_id=stock_id,
                    date=date_str,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                )
                self.db.add(new_ohlcv)
                rows_inserted += 1

        await self.db.flush()
        return rows_inserted

    # ── CSV Import ──

    async def import_csv(self, symbol: str, csv_content: str, name: str | None = None) -> int:
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
        stock_id = await self.get_or_create_stock(symbol, name=name)

        reader = csv.DictReader(io.StringIO(csv_content))
        column_map = self._build_column_map(reader.fieldnames or [])

        rows_inserted = 0
        for row in reader:
            date_str = self._parse_date(row[column_map["date"]])

            # Check if record exists
            result = await self.db.execute(
                select(OHLCV).where(OHLCV.stock_id == stock_id, OHLCV.date == date_str)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.open = float(row[column_map["open"]])
                existing.high = float(row[column_map["high"]])
                existing.low = float(row[column_map["low"]])
                existing.close = float(row[column_map["close"]])
                existing.volume = int(float(row[column_map["volume"]]))
            else:
                # Insert new record
                new_ohlcv = OHLCV(
                    stock_id=stock_id,
                    date=date_str,
                    open=float(row[column_map["open"]]),
                    high=float(row[column_map["high"]]),
                    low=float(row[column_map["low"]]),
                    close=float(row[column_map["close"]]),
                    volume=int(float(row[column_map["volume"]])),
                )
                self.db.add(new_ohlcv)
                rows_inserted += 1

        await self.db.flush()
        return rows_inserted

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
                    f"Missing required column '{key}' in CSV. " f"Found columns: {fieldnames}"
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
                return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: '{date_str}'")

    # ── Data Query ──

    async def get_ohlcv(
        self, symbol: str, start_date: str | None = None, end_date: str | None = None
    ) -> pd.DataFrame:
        """Query OHLCV data for a symbol within a date range.

        Args:
            symbol: Stock ticker symbol.
            start_date: Optional start date (YYYY-MM-DD), inclusive.
            end_date: Optional end date (YYYY-MM-DD), inclusive.

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.
            Index is a DatetimeIndex. Returns empty DataFrame if no data found.
        """
        # Build query
        query = (
            select(OHLCV)
            .join(Stock)
            .where(Stock.symbol == symbol.upper())
        )

        if start_date:
            query = query.where(OHLCV.date >= start_date)
        if end_date:
            query = query.where(OHLCV.date <= end_date)

        query = query.order_by(OHLCV.date)

        # Execute query
        result = await self.db.execute(query)
        ohlcv_records = result.scalars().all()

        if not ohlcv_records:
            return pd.DataFrame()

        # Convert to DataFrame
        data = [
            {
                "date": record.date,
                "open": record.open,
                "high": record.high,
                "low": record.low,
                "close": record.close,
                "volume": record.volume,
            }
            for record in ohlcv_records
        ]

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        return df

    async def get_date_range(self, symbol: str) -> tuple[str, str] | None:
        """Return the earliest and latest dates for a symbol.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Tuple of (earliest_date, latest_date) strings, or None if no data.
        """
        from sqlalchemy import func

        # Get stock ID first
        result = await self.db.execute(select(Stock).where(Stock.symbol == symbol.upper()))
        stock = result.scalar_one_or_none()

        if not stock:
            return None

        # Get min and max dates
        result = await self.db.execute(
            select(func.min(OHLCV.date), func.max(OHLCV.date)).where(OHLCV.stock_id == stock.id)
        )
        min_date, max_date = result.one()

        if min_date is None:
            return None

        return (min_date, max_date)

    async def delete_stock_data(self, symbol: str) -> bool:
        """Delete all OHLCV data and metadata for a symbol.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            True if data was deleted, False if symbol not found.
        """
        result = await self.db.execute(select(Stock).where(Stock.symbol == symbol.upper()))
        stock = result.scalar_one_or_none()

        if not stock:
            return False

        # Delete OHLCV data (cascades automatically)
        await self.db.delete(stock)
        await self.db.flush()
        return True
