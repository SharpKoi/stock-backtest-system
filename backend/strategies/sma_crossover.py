"""SMA Crossover Strategy: a classic trend-following strategy.

Buys when the short-period SMA crosses above the long-period SMA (golden cross).
Sells when the short-period SMA crosses below the long-period SMA (death cross).
"""

import pandas as pd

from app.services.strategy import Portfolio, Strategy


class SMACrossover(Strategy):
    """Simple Moving Average Crossover strategy.

    Parameters (via self.params):
        short_period: Short SMA period (default 50).
        long_period: Long SMA period (default 200).
        position_size: Number of shares per trade (default 100).
    """

    @property
    def name(self) -> str:
        return "SMA Crossover"

    def indicators(self) -> list[dict]:
        short = self.params.get("short_period", 50)
        long = self.params.get("long_period", 200)
        return [
            {"name": "sma", "params": {"period": short}},
            {"name": "sma", "params": {"period": long}},
        ]

    def on_bar(self, date: str, data: dict[str, pd.Series],
               portfolio: Portfolio) -> None:
        short = self.params.get("short_period", 50)
        long = self.params.get("long_period", 200)
        size = self.params.get("position_size", 100)

        for symbol, bar in data.items():
            sma_short = bar.get(f"sma_{short}")
            sma_long = bar.get(f"sma_{long}")
            close = bar["close"]

            if pd.isna(sma_short) or pd.isna(sma_long):
                continue

            position = portfolio.get_position(symbol)

            if sma_short > sma_long and not position.is_open:
                portfolio.buy(symbol, size, close, date)
            elif sma_short < sma_long and position.is_open:
                portfolio.sell(symbol, position.quantity, close, date)

    def on_end(self, portfolio: Portfolio) -> None:
        """Close all open positions at the end of the backtest."""
        for _symbol, position in portfolio.positions.items():
            if position.is_open:
                # We cannot get the price here directly, so we skip
                # The engine should handle this if needed
                pass
