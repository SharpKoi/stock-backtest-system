"""Backtest Engine: time-series simulation of trading strategies.

Iterates through historical data day by day, calling the strategy's on_bar()
method, managing the portfolio, and collecting results.
"""

import logging

import pandas as pd

from app.services.indicators import compute_indicators
from app.services.strategy import Portfolio, Strategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Runs a backtest simulation for a given strategy and data.

    The engine:
    1. Pre-computes all indicators for each symbol
    2. Iterates through each trading day
    3. Calls the strategy's on_bar() with current data
    4. Records portfolio equity at each step

    Attributes:
        strategy: The Strategy instance to simulate.
        initial_capital: Starting cash amount.
        commission_rate: Commission rate per trade.
    """

    def __init__(self, strategy: Strategy,
                 initial_capital: float = 100_000.0,
                 commission_rate: float = 0.001):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate

    def run(self, data: dict[str, pd.DataFrame]) -> Portfolio:
        """Execute the backtest.

        Args:
            data: Dict mapping stock symbol to OHLCV DataFrame.
                  Each DataFrame must have a DatetimeIndex and columns:
                  open, high, low, close, volume.

        Returns:
            Portfolio object containing trades, equity history,
            and final positions.

        Raises:
            ValueError: If data is empty or has no overlapping dates.
        """
        if not data:
            raise ValueError("No data provided for backtest")

        prepared_data = self._prepare_data(data)
        trading_dates = self._get_trading_dates(prepared_data)

        if len(trading_dates) == 0:
            raise ValueError("No overlapping trading dates found")

        portfolio = Portfolio(
            initial_capital=self.initial_capital,
            commission_rate=self.commission_rate,
        )

        symbols = list(prepared_data.keys())
        self.strategy.on_start(portfolio, symbols)

        logger.info(
            "Starting backtest: %s | %d symbols | %d trading days",
            self.strategy.name, len(symbols), len(trading_dates)
        )

        for date in trading_dates:
            date_str = date.strftime("%Y-%m-%d")
            bar_data = self._get_bar_data(prepared_data, date)

            if bar_data:
                self.strategy.on_bar(date_str, bar_data, portfolio)

            current_prices = self._get_current_prices(prepared_data, date)
            portfolio.record_equity(date_str, current_prices)

        self.strategy.on_end(portfolio)

        logger.info(
            "Backtest complete: %d trades | Final equity: %.2f",
            len(portfolio.trades),
            portfolio.equity_history[-1]["equity"] if portfolio.equity_history else 0
        )

        return portfolio

    def _prepare_data(self,
                      data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """Pre-compute indicators for each symbol's DataFrame.

        Args:
            data: Raw OHLCV data per symbol.

        Returns:
            Dict of DataFrames with indicators added as new columns.
        """
        indicator_configs = self.strategy.indicators()
        prepared = {}

        for symbol, df in data.items():
            if df.empty:
                logger.warning("Skipping empty data for %s", symbol)
                continue

            if indicator_configs:
                prepared[symbol] = compute_indicators(df, indicator_configs)
            else:
                prepared[symbol] = df.copy()

        return prepared

    def _get_trading_dates(self,
                           data: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
        """Find the union of all trading dates across symbols.

        Uses the intersection approach: only dates where ALL symbols have data,
        ensuring the strategy always has complete data for each bar.

        Args:
            data: Prepared data dict.

        Returns:
            Sorted DatetimeIndex of common trading dates.
        """
        if not data:
            return pd.DatetimeIndex([])

        date_sets = [set(df.index) for df in data.values()]

        # Use intersection so that on each bar, all symbols have data
        common_dates = date_sets[0]
        for ds in date_sets[1:]:
            common_dates = common_dates.intersection(ds)

        return pd.DatetimeIndex(sorted(common_dates))

    def _get_bar_data(self, data: dict[str, pd.DataFrame],
                      date: pd.Timestamp) -> dict[str, pd.Series]:
        """Extract the row for a specific date from each symbol's data.

        Args:
            data: Prepared data dict.
            date: The date to extract.

        Returns:
            Dict mapping symbol to a Series of values for that date.
        """
        bar_data = {}
        for symbol, df in data.items():
            if date in df.index:
                bar_data[symbol] = df.loc[date]
        return bar_data

    def _get_current_prices(self, data: dict[str, pd.DataFrame],
                            date: pd.Timestamp) -> dict[str, float]:
        """Get closing prices for all symbols on a given date.

        Args:
            data: Prepared data dict.
            date: The target date.

        Returns:
            Dict mapping symbol to the close price on that date.
        """
        prices = {}
        for symbol, df in data.items():
            if date in df.index:
                prices[symbol] = float(df.loc[date, "close"])
        return prices
