"""Strategy interface and portfolio management for backtesting.

This module re-exports core classes from vici-trade-sdk for backward compatibility.
Backend code can continue importing from app.services.strategy, while users install
and import from vici_trade_sdk directly.
"""

from vici_trade_sdk import Portfolio, Position, Side, Strategy, Trade

__all__ = ["Strategy", "Portfolio", "Position", "Trade", "Side"]
