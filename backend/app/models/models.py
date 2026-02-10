"""SQLAlchemy ORM models for the backtesting system.

Defines database schema using SQLAlchemy 2.0 declarative mapping.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """User authentication table."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    backtests: Mapped[list["Backtest"]] = relationship(
        "Backtest", back_populates="user", cascade="all, delete-orphan"
    )


class Stock(Base):
    """Stock metadata table."""

    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    ohlcv_data: Mapped[list["OHLCV"]] = relationship(
        "OHLCV", back_populates="stock", cascade="all, delete-orphan"
    )


class OHLCV(Base):
    """OHLCV (Open, High, Low, Close, Volume) price data table."""

    __tablename__ = "ohlcv"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD format
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    stock: Mapped["Stock"] = relationship("Stock", back_populates="ohlcv_data")

    # Indexes
    __table_args__ = (
        Index("idx_ohlcv_stock_date", "stock_id", "date"),
        Index("idx_ohlcv_stock_id", "stock_id"),
    )


class Backtest(Base):
    """Backtest metadata and configuration table."""

    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    symbols: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded list
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    end_date: Mapped[str] = mapped_column(String(10), nullable=False)
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.001")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="backtests")
    trades: Mapped[list["Trade"]] = relationship(
        "Trade", back_populates="backtest", cascade="all, delete-orphan"
    )
    result: Mapped["BacktestResult | None"] = relationship(
        "BacktestResult", back_populates="backtest", cascade="all, delete-orphan", uselist=False
    )


class Trade(Base):
    """Individual trade records from backtests."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    backtest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # 'BUY' or 'SELL'
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    commission: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    date: Mapped[str] = mapped_column(String(10), nullable=False)

    # Relationships
    backtest: Mapped["Backtest"] = relationship("Backtest", back_populates="trades")


class BacktestResult(Base):
    """Backtest results with performance metrics and equity curve."""

    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    backtest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded metrics
    equity_curve_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded curve

    # Relationships
    backtest: Mapped["Backtest"] = relationship("Backtest", back_populates="result")
