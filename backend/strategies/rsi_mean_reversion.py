"""RSI Mean Reversion Strategy.

Buys when RSI drops below the oversold threshold (default 30),
sells when RSI rises above the overbought threshold (default 70).
"""

import pandas as pd

from app.services.strategy import Portfolio, Strategy


class RSIMeanReversion(Strategy):
    """RSI-based mean reversion strategy.

    Parameters (via self.params):
        rsi_period: RSI calculation period (default 14).
        oversold: RSI level to trigger buy (default 30).
        overbought: RSI level to trigger sell (default 70).
        position_size: Number of shares per trade (default 100).
    """

    @property
    def name(self) -> str:
        return "RSI Mean Reversion"

    def indicators(self) -> list[dict]:
        period = self.params.get("rsi_period", 14)
        return [
            {"name": "rsi", "params": {"period": period}},
        ]

    def on_bar(self, date: str, data: dict[str, pd.Series],
               portfolio: Portfolio) -> None:
        period = self.params.get("rsi_period", 14)
        oversold = self.params.get("oversold", 30)
        overbought = self.params.get("overbought", 70)
        size = self.params.get("position_size", 100)

        for symbol, bar in data.items():
            rsi_val = bar.get(f"rsi_{period}")
            close = bar["close"]

            if pd.isna(rsi_val):
                continue

            position = portfolio.get_position(symbol)

            if rsi_val < oversold and not position.is_open:
                portfolio.buy(symbol, size, close, date)
            elif rsi_val > overbought and position.is_open:
                portfolio.sell(symbol, position.quantity, close, date)
