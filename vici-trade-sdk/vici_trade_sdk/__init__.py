"""Vici Trade SDK - Core classes for building trading strategies.

This package provides the essential building blocks for creating custom
backtesting strategies:
- Strategy: Base class for implementing trading logic
- Portfolio: Interface for managing positions and executing trades
- Position: Representation of an open position
- Trade: Record of an executed trade
- Side: Enum for trade direction (BUY/SELL)
"""

from vici_trade_sdk.portfolio import Portfolio, Position, Side, Trade
from vici_trade_sdk.strategy import Strategy

__version__ = "0.1.0"

__all__ = [
    "Strategy",
    "Portfolio",
    "Position",
    "Trade",
    "Side",
]
