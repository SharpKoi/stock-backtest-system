"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field


class StockInfo(BaseModel):
    """Stock metadata."""

    id: int | None = None
    symbol: str
    name: str | None = None
    exchange: str | None = None
    sector: str | None = None


class OHLCVBar(BaseModel):
    """A single OHLCV bar."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class DownloadRequest(BaseModel):
    """Request to download stock data."""

    symbol: str
    start_date: str | None = None
    end_date: str | None = None
    period: str | None = "5y"


class BacktestRequest(BaseModel):
    """Request to run a backtest."""

    name: str
    strategy_name: str
    symbols: list[str]
    start_date: str
    end_date: str
    initial_capital: float = Field(default=100_000.0, gt=0)
    commission_rate: float = Field(default=0.001, ge=0, le=0.1)
    strategy_params: dict = Field(default_factory=dict)


class TradeRecord(BaseModel):
    """A single trade record."""

    id: int | None = None
    backtest_id: int
    symbol: str
    side: str
    quantity: float
    price: float
    commission: float = 0.0
    date: str


class PerformanceMetrics(BaseModel):
    """Computed performance metrics for a backtest."""

    total_return: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    sharpe_ratio: float
    profit_factor: float
    avg_trade_return_pct: float
    max_consecutive_wins: int
    max_consecutive_losses: int


class BacktestResult(BaseModel):
    """Complete result of a backtest run."""

    backtest_id: int
    name: str
    strategy_name: str
    symbols: list[str]
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    metrics: PerformanceMetrics
    trades: list[TradeRecord]
    equity_curve: list[dict]


class BacktestSummary(BaseModel):
    """Summary of a backtest for listing."""

    id: int
    name: str
    strategy_name: str
    symbols: list[str]
    start_date: str
    end_date: str
    initial_capital: float
    status: str
    created_at: str


class CSVImportRequest(BaseModel):
    """Request to import CSV data."""

    symbol: str
    name: str | None = None
