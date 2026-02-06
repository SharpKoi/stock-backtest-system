# Vici Trade SDK

A Python SDK for building custom trading strategies in the Vici Stock Backtesting System.

## Overview

The Vici Trade SDK provides the essential building blocks for creating backtesting strategies:

- **Strategy**: Base class for implementing trading logic
- **Portfolio**: Interface for managing positions and executing trades
- **Position**: Representation of an open position
- **Trade**: Record of an executed trade
- **Side**: Enum for trade direction (BUY/SELL)

## Installation

### For Strategy Writers

Install the SDK to write custom strategies:

```bash
pip install vici-trade-sdk
```

### For Local Development

If you're developing the SDK itself:

```bash
cd vici-trade-sdk
poetry install
```

For developing the backend with local SDK changes:

```bash
# From backend directory
poetry add ../vici-trade-sdk
```

This adds the SDK as a path dependency to the backend, enabling immediate reflection of SDK changes during development.

## Quick Start

Create a strategy by inheriting from `Strategy` and implementing the required methods:

```python
from vici_trade_sdk import Strategy, Portfolio
import pandas as pd

class GoldenCrossStrategy(Strategy):
    @property
    def name(self) -> str:
        return "Golden Cross Strategy"

    def indicators(self) -> list[dict]:
        """Define indicators to pre-compute."""
        return [
            {"name": "sma", "params": {"period": 50}},
            {"name": "sma", "params": {"period": 200}},
        ]

    def on_bar(self, date: str, data: dict[str, pd.Series],
               portfolio: Portfolio) -> None:
        """Trading logic executed on each bar."""
        for symbol in data:
            sma50 = data[symbol]["sma_50"]
            sma200 = data[symbol]["sma_200"]

            # Golden cross: buy when fast MA crosses above slow MA
            if sma50 > sma200:
                if not portfolio.get_position(symbol).is_open:
                    portfolio.buy(symbol, 100, data[symbol]["close"], date)
            # Death cross: sell when fast MA crosses below slow MA
            elif sma50 < sma200:
                if portfolio.get_position(symbol).is_open:
                    portfolio.sell(
                        symbol,
                        portfolio.get_position(symbol).quantity,
                        data[symbol]["close"],
                        date
                    )
```

## Core Concepts

### Strategy Lifecycle

1. **Initialization**: `__init__()` is called with optional parameters
2. **Indicator Setup**: `indicators()` defines what technical indicators to pre-compute
3. **Start**: `on_start()` is called once before the backtest begins
4. **Execution**: `on_bar()` is called for each time step with market data and portfolio
5. **End**: `on_end()` is called once after the backtest completes

### Portfolio Management

The `Portfolio` object provides methods to:

- **Buy shares**: `portfolio.buy(symbol, quantity, price, date)`
- **Sell shares**: `portfolio.sell(symbol, quantity, price, date)`
- **Check positions**: `portfolio.get_position(symbol)`
- **Track equity**: `portfolio.total_equity(current_prices)`

### Position Tracking

Each `Position` tracks:

- Symbol and quantity held
- Average entry price
- Cost basis
- Market value and unrealized P&L

### Trade History

All executed trades are recorded with:

- Symbol, side (BUY/SELL), quantity, price
- Commission charged
- Trade date

## Strategy Storage

Strategies are stored in the user workspace directory at:

```
~/.vici-backtest/strategies/
```

Each strategy file should:

1. Import from `vici_trade_sdk`
2. Define a class inheriting from `Strategy`
3. Implement `name`, `indicators()`, and `on_bar()`

The backend system will automatically discover and load all valid strategy files from this directory.

## Example Strategies

### Simple Moving Average Crossover

```python
from vici_trade_sdk import Strategy, Portfolio
import pandas as pd

class SMACrossover(Strategy):
    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.fast_period = self.params.get("fast_period", 20)
        self.slow_period = self.params.get("slow_period", 50)

    @property
    def name(self) -> str:
        return f"SMA Crossover ({self.fast_period}/{self.slow_period})"

    def indicators(self) -> list[dict]:
        return [
            {"name": "sma", "params": {"period": self.fast_period}},
            {"name": "sma", "params": {"period": self.slow_period}},
        ]

    def on_bar(self, date: str, data: dict[str, pd.Series],
               portfolio: Portfolio) -> None:
        for symbol in data:
            fast_sma = data[symbol][f"sma_{self.fast_period}"]
            slow_sma = data[symbol][f"sma_{self.slow_period}"]

            position = portfolio.get_position(symbol)

            if fast_sma > slow_sma and not position.is_open:
                # Buy signal
                portfolio.buy(symbol, 100, data[symbol]["close"], date)
            elif fast_sma < slow_sma and position.is_open:
                # Sell signal
                portfolio.sell(symbol, position.quantity,
                             data[symbol]["close"], date)
```

### RSI Mean Reversion

```python
from vici_trade_sdk import Strategy, Portfolio
import pandas as pd

class RSIMeanReversion(Strategy):
    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.oversold = self.params.get("oversold", 30)
        self.overbought = self.params.get("overbought", 70)

    @property
    def name(self) -> str:
        return f"RSI Mean Reversion ({self.oversold}/{self.overbought})"

    def indicators(self) -> list[dict]:
        return [
            {"name": "rsi", "params": {"period": self.rsi_period}},
        ]

    def on_bar(self, date: str, data: dict[str, pd.Series],
               portfolio: Portfolio) -> None:
        for symbol in data:
            rsi = data[symbol][f"rsi_{self.rsi_period}"]
            position = portfolio.get_position(symbol)

            if rsi < self.oversold and not position.is_open:
                # Oversold: buy
                portfolio.buy(symbol, 100, data[symbol]["close"], date)
            elif rsi > self.overbought and position.is_open:
                # Overbought: sell
                portfolio.sell(symbol, position.quantity,
                             data[symbol]["close"], date)
```

## Available Indicators

The backend system provides built-in indicators that can be referenced in `indicators()`:

- **sma**: Simple Moving Average
  - Parameters: `period` (int)
- **ema**: Exponential Moving Average
  - Parameters: `period` (int)
- **rsi**: Relative Strength Index
  - Parameters: `period` (int)
- **macd**: Moving Average Convergence Divergence
  - Parameters: `fast_period` (int), `slow_period` (int), `signal_period` (int)
- **bbands**: Bollinger Bands
  - Parameters: `period` (int), `std_dev` (float)

## Development

### Running Tests

```bash
poetry run pytest
```

### Building the Package

```bash
poetry build
```

### Publishing

```bash
poetry publish
```

## License

MIT

## Contributing

Contributions are welcome. Please submit issues and pull requests to the main repository.
