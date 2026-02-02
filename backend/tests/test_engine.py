"""Tests for the Backtest Engine."""

import pandas as pd
import pytest

from app.services.engine import BacktestEngine
from app.services.strategy import Strategy


class AlwaysBuyStrategy(Strategy):
    """Test strategy that buys on every bar if not holding."""

    @property
    def name(self):
        return "Always Buy"

    def on_bar(self, date, data, portfolio):
        for symbol, bar in data.items():
            position = portfolio.get_position(symbol)
            if not position.is_open:
                portfolio.buy(symbol, 10, bar["close"], date)


class BuyAndSellStrategy(Strategy):
    """Test strategy that alternates buy and sell."""

    def __init__(self, params=None):
        super().__init__(params)
        self._bar_count = 0

    @property
    def name(self):
        return "Buy and Sell"

    def on_bar(self, date, data, portfolio):
        self._bar_count += 1
        for symbol, bar in data.items():
            position = portfolio.get_position(symbol)
            if self._bar_count % 10 == 1 and not position.is_open:
                portfolio.buy(symbol, 10, bar["close"], date)
            elif self._bar_count % 10 == 5 and position.is_open:
                portfolio.sell(symbol, position.quantity, bar["close"], date)


class WithIndicatorStrategy(Strategy):
    """Test strategy that uses SMA indicator."""

    @property
    def name(self):
        return "SMA Test"

    def indicators(self):
        return [{"name": "sma", "params": {"period": 5}}]

    def on_bar(self, date, data, portfolio):
        for symbol, bar in data.items():
            sma_val = bar.get("sma_5")
            if pd.notna(sma_val) and bar["close"] > sma_val:
                position = portfolio.get_position(symbol)
                if not position.is_open:
                    portfolio.buy(symbol, 5, bar["close"], date)


class TestBacktestEngine:
    def test_empty_data_raises(self):
        engine = BacktestEngine(AlwaysBuyStrategy())
        with pytest.raises(ValueError, match="No data provided"):
            engine.run({})

    def test_basic_run(self, sample_ohlcv):
        engine = BacktestEngine(AlwaysBuyStrategy(), initial_capital=100_000)
        portfolio = engine.run({"TEST": sample_ohlcv})
        assert len(portfolio.equity_history) > 0
        assert len(portfolio.trades) > 0

    def test_equity_recorded_every_bar(self, sample_ohlcv):
        engine = BacktestEngine(AlwaysBuyStrategy(), initial_capital=100_000)
        portfolio = engine.run({"TEST": sample_ohlcv})
        assert len(portfolio.equity_history) == len(sample_ohlcv)

    def test_buy_and_sell_trades(self, sample_ohlcv):
        engine = BacktestEngine(BuyAndSellStrategy(), initial_capital=100_000)
        portfolio = engine.run({"TEST": sample_ohlcv})
        buys = [t for t in portfolio.trades if t.side.value == "BUY"]
        sells = [t for t in portfolio.trades if t.side.value == "SELL"]
        # Should have roughly equal buys and sells
        assert len(buys) > 0
        assert len(sells) > 0

    def test_indicators_precomputed(self, sample_ohlcv):
        engine = BacktestEngine(WithIndicatorStrategy(), initial_capital=100_000)
        portfolio = engine.run({"TEST": sample_ohlcv})
        # Strategy only buys when close > SMA, so should have some trades
        assert len(portfolio.equity_history) > 0

    def test_multi_stock(self, sample_ohlcv):
        # Use same data for two symbols
        engine = BacktestEngine(AlwaysBuyStrategy(), initial_capital=200_000)
        data = {"STOCK_A": sample_ohlcv, "STOCK_B": sample_ohlcv.copy()}
        portfolio = engine.run(data)
        symbols_traded = {t.symbol for t in portfolio.trades}
        assert "STOCK_A" in symbols_traded
        assert "STOCK_B" in symbols_traded

    def test_commission_deducted(self, sample_ohlcv):
        engine = BacktestEngine(
            AlwaysBuyStrategy(), initial_capital=100_000, commission_rate=0.01
        )
        portfolio = engine.run({"TEST": sample_ohlcv})
        total_commission = sum(t.commission for t in portfolio.trades)
        assert total_commission > 0

    def test_initial_capital_preserved_with_no_trades(self, sample_ohlcv):
        class DoNothingStrategy(Strategy):
            @property
            def name(self):
                return "Do Nothing"

            def on_bar(self, date, data, portfolio):
                pass

        engine = BacktestEngine(DoNothingStrategy(), initial_capital=50_000)
        portfolio = engine.run({"TEST": sample_ohlcv})
        assert portfolio.equity_history[-1]["equity"] == 50_000
        assert len(portfolio.trades) == 0
