"""Strategy interface and portfolio management for backtesting.

Provides the Strategy base class that users inherit to define trading rules,
plus Position and Portfolio classes for tracking state during simulation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd


class Side(str, Enum):
    """Trade direction."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Trade:
    """Record of a single executed trade."""

    symbol: str
    side: Side
    quantity: float
    price: float
    commission: float
    date: str


@dataclass
class Position:
    """An open position in a single stock.

    Tracks average entry price and current quantity.
    """

    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    cost_basis: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.quantity > 0

    def market_value(self, current_price: float) -> float:
        """Calculate current market value of the position."""
        return self.quantity * current_price

    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized profit/loss."""
        return self.market_value(current_price) - self.cost_basis


@dataclass
class Portfolio:
    """Tracks all positions, cash, and trade history during a backtest.

    This is the primary interface strategies use to place orders
    and check account state.
    """

    initial_capital: float
    commission_rate: float = 0.001
    cash: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)
    equity_history: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if self.cash == 0.0:
            self.cash = self.initial_capital

    def get_position(self, symbol: str) -> Position:
        """Return the position for a symbol, creating one if needed.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            The Position object for the symbol.
        """
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]

    def buy(self, symbol: str, quantity: float, price: float,
            date: str) -> Trade | None:
        """Execute a buy order.

        Args:
            symbol: Stock ticker symbol.
            quantity: Number of shares to buy.
            price: Price per share.
            date: Date string of the trade.

        Returns:
            Trade record if executed, None if insufficient cash.
        """
        cost = quantity * price
        commission = cost * self.commission_rate
        total_cost = cost + commission

        if total_cost > self.cash:
            return None

        self.cash -= total_cost
        position = self.get_position(symbol)
        new_cost_basis = position.cost_basis + cost
        new_quantity = position.quantity + quantity
        position.avg_price = new_cost_basis / new_quantity if new_quantity > 0 else 0
        position.quantity = new_quantity
        position.cost_basis = new_cost_basis

        trade = Trade(
            symbol=symbol, side=Side.BUY, quantity=quantity,
            price=price, commission=commission, date=date
        )
        self.trades.append(trade)
        return trade

    def sell(self, symbol: str, quantity: float, price: float,
             date: str) -> Trade | None:
        """Execute a sell order.

        Args:
            symbol: Stock ticker symbol.
            quantity: Number of shares to sell.
            price: Price per share.
            date: Date string of the trade.

        Returns:
            Trade record if executed, None if insufficient shares.
        """
        position = self.get_position(symbol)
        if quantity > position.quantity:
            return None

        revenue = quantity * price
        commission = revenue * self.commission_rate
        net_revenue = revenue - commission

        self.cash += net_revenue

        # Reduce cost basis proportionally
        sell_ratio = quantity / position.quantity
        position.cost_basis -= position.cost_basis * sell_ratio
        position.quantity -= quantity

        if position.quantity < 1e-9:
            position.quantity = 0.0
            position.cost_basis = 0.0
            position.avg_price = 0.0

        trade = Trade(
            symbol=symbol, side=Side.SELL, quantity=quantity,
            price=price, commission=commission, date=date
        )
        self.trades.append(trade)
        return trade

    def total_equity(self, current_prices: dict[str, float]) -> float:
        """Calculate total portfolio value (cash + position market values).

        Args:
            current_prices: Dict mapping symbol to current price.

        Returns:
            Total equity value.
        """
        equity = self.cash
        for symbol, position in self.positions.items():
            if position.is_open and symbol in current_prices:
                equity += position.market_value(current_prices[symbol])
        return equity

    def record_equity(self, date: str,
                      current_prices: dict[str, float]) -> None:
        """Snapshot current equity for the equity curve.

        Args:
            date: Date string.
            current_prices: Dict mapping symbol to current price.
        """
        equity = self.total_equity(current_prices)
        self.equity_history.append({
            "date": date,
            "equity": equity,
            "cash": self.cash,
        })


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
