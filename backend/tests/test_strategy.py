"""Tests for the Strategy interface and Portfolio management."""

import pytest

from app.services.strategy import Portfolio, Position, Side, Strategy


class TestPosition:
    def test_new_position_is_closed(self):
        pos = Position(symbol="AAPL")
        assert not pos.is_open
        assert pos.quantity == 0

    def test_market_value(self):
        pos = Position(symbol="AAPL", quantity=10, avg_price=150.0, cost_basis=1500.0)
        assert pos.market_value(160.0) == 1600.0

    def test_unrealized_pnl(self):
        pos = Position(symbol="AAPL", quantity=10, avg_price=150.0, cost_basis=1500.0)
        assert pos.unrealized_pnl(160.0) == 100.0
        assert pos.unrealized_pnl(140.0) == -100.0


class TestPortfolio:
    def test_initial_state(self):
        portfolio = Portfolio(initial_capital=100_000, commission_rate=0.001)
        assert portfolio.cash == 100_000
        assert portfolio.initial_capital == 100_000
        assert len(portfolio.positions) == 0
        assert len(portfolio.trades) == 0

    def test_buy_success(self):
        portfolio = Portfolio(initial_capital=100_000, commission_rate=0.001)
        trade = portfolio.buy("AAPL", 10, 150.0, "2024-01-02")
        assert trade is not None
        assert trade.side == Side.BUY
        assert trade.quantity == 10
        assert trade.price == 150.0
        # 10 * 150 = 1500, commission = 1.5, total = 1501.5
        assert portfolio.cash == pytest.approx(100_000 - 1501.5)
        position = portfolio.get_position("AAPL")
        assert position.quantity == 10

    def test_buy_insufficient_cash(self):
        portfolio = Portfolio(initial_capital=1000, commission_rate=0.001)
        trade = portfolio.buy("AAPL", 10, 150.0, "2024-01-02")
        assert trade is None
        assert portfolio.cash == 1000

    def test_sell_success(self):
        portfolio = Portfolio(initial_capital=100_000, commission_rate=0.001)
        portfolio.buy("AAPL", 10, 150.0, "2024-01-02")
        trade = portfolio.sell("AAPL", 10, 160.0, "2024-01-03")
        assert trade is not None
        assert trade.side == Side.SELL
        assert trade.quantity == 10
        # After sell, position should be closed
        position = portfolio.get_position("AAPL")
        assert not position.is_open

    def test_sell_insufficient_shares(self):
        portfolio = Portfolio(initial_capital=100_000, commission_rate=0.001)
        portfolio.buy("AAPL", 5, 150.0, "2024-01-02")
        trade = portfolio.sell("AAPL", 10, 160.0, "2024-01-03")
        assert trade is None

    def test_partial_sell(self):
        portfolio = Portfolio(initial_capital=100_000, commission_rate=0.001)
        portfolio.buy("AAPL", 20, 150.0, "2024-01-02")
        portfolio.sell("AAPL", 10, 160.0, "2024-01-03")
        position = portfolio.get_position("AAPL")
        assert position.quantity == 10
        assert position.is_open

    def test_total_equity(self):
        portfolio = Portfolio(initial_capital=100_000, commission_rate=0)
        portfolio.buy("AAPL", 10, 150.0, "2024-01-02")
        equity = portfolio.total_equity({"AAPL": 160.0})
        # cash: 100000 - 1500 = 98500, position: 10 * 160 = 1600
        assert equity == pytest.approx(100_100)

    def test_record_equity(self):
        portfolio = Portfolio(initial_capital=100_000, commission_rate=0)
        portfolio.record_equity("2024-01-02", {})
        assert len(portfolio.equity_history) == 1
        assert portfolio.equity_history[0]["equity"] == 100_000

    def test_multiple_symbols(self):
        portfolio = Portfolio(initial_capital=200_000, commission_rate=0.001)
        portfolio.buy("AAPL", 10, 150.0, "2024-01-02")
        portfolio.buy("GOOGL", 5, 180.0, "2024-01-02")
        assert portfolio.get_position("AAPL").quantity == 10
        assert portfolio.get_position("GOOGL").quantity == 5
        assert len(portfolio.trades) == 2

    def test_trade_records_accumulated(self):
        portfolio = Portfolio(initial_capital=100_000, commission_rate=0.001)
        portfolio.buy("AAPL", 10, 150.0, "2024-01-02")
        portfolio.sell("AAPL", 10, 160.0, "2024-01-03")
        portfolio.buy("AAPL", 5, 155.0, "2024-01-04")
        assert len(portfolio.trades) == 3


class TestStrategyInterface:
    def test_strategy_is_abstract(self):
        with pytest.raises(TypeError):
            Strategy()  # type: ignore

    def test_concrete_strategy(self):
        class DummyStrategy(Strategy):
            @property
            def name(self):
                return "Dummy"

            def on_bar(self, date, data, portfolio):
                pass

        s = DummyStrategy()
        assert s.name == "Dummy"
        assert s.indicators() == []

    def test_strategy_with_params(self):
        class ParamStrategy(Strategy):
            @property
            def name(self):
                return "Param"

            def on_bar(self, date, data, portfolio):
                pass

        s = ParamStrategy(params={"period": 20})
        assert s.params["period"] == 20
