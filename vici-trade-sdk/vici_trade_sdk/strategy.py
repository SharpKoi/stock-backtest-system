"""Strategy interface for backtesting.

Provides the Strategy base class that users inherit to define trading rules.
"""

from abc import ABC, abstractmethod

import pandas as pd

from vici_trade_sdk.portfolio import Portfolio


class Strategy(ABC):
    """Base class for user-defined trading strategies.

    Users inherit this class and implement:
    - indicators(): returns indicator configs to pre-compute
    - on_bar(): called for each time step with current data and portfolio

    Example usage:
        class GoldenCross(Strategy):
            @property
            def name(self):
                return "Golden Cross"

            def indicators(self):
                return [
                    {"name": "sma", "params": {"period": 50}},
                    {"name": "sma", "params": {"period": 200}},
                ]

            def on_bar(self, date, data, portfolio):
                for symbol in data:
                    sma50 = data[symbol]["sma_50"]
                    sma200 = data[symbol]["sma_200"]
                    if sma50 > sma200:
                        portfolio.buy(symbol, 10, data[symbol]["close"], date)
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the strategy name."""

    def indicators(self) -> list[dict]:
        """Return indicator configurations to pre-compute before backtesting.

        Override this to specify indicators the strategy needs. Each dict
        should have at minimum a "name" key matching a built-in indicator,
        and optionally "params" and "column" keys.

        Returns:
            List of indicator config dicts.
        """
        return []

    def on_start(self, portfolio: Portfolio,
                 symbols: list[str]) -> None:
        """Called once before the backtest begins.

        Override to perform initialization logic.

        Args:
            portfolio: The portfolio instance.
            symbols: List of symbols being traded.
        """

    @abstractmethod
    def on_bar(self, date: str, data: dict[str, pd.Series],
               portfolio: Portfolio) -> None:
        """Called for each time step (bar) during the backtest.

        This is where the strategy logic lives. Use portfolio.buy() and
        portfolio.sell() to place orders.

        Args:
            date: The current date string (YYYY-MM-DD).
            data: Dict mapping symbol to a Series containing OHLCV values
                  and pre-computed indicator values for this bar.
            portfolio: The portfolio instance for placing orders.
        """

    def on_end(self, portfolio: Portfolio) -> None:
        """Called once after the backtest ends.

        Override to perform cleanup or final-day logic (e.g., close all
        positions).

        Args:
            portfolio: The portfolio instance.
        """
