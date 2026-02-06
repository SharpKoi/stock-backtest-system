"""Portfolio management classes for backtesting.

Provides Position, Trade, Side, and Portfolio classes for tracking state during simulation.
"""

from dataclasses import dataclass, field
from enum import Enum


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
