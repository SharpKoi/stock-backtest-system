"""Tests for the Performance Calculator."""


from app.services.performance import (
    _annualized_return,
    _consecutive_streaks,
    _max_drawdown,
    _sharpe_ratio,
    _trade_statistics,
    calculate_performance,
)
from app.services.strategy import Portfolio, Side, Trade


def _make_portfolio_with_equity(equity_values, initial_capital=100_000):
    """Create a Portfolio with a pre-filled equity history."""
    portfolio = Portfolio(initial_capital=initial_capital)
    for i, equity in enumerate(equity_values):
        portfolio.equity_history.append({
            "date": f"2024-01-{i + 1:02d}",
            "equity": equity,
            "cash": equity,
        })
    return portfolio


def _make_trade(symbol, side, qty, price, commission=0, date="2024-01-01"):
    return Trade(
        symbol=symbol, side=side, quantity=qty,
        price=price, commission=commission, date=date,
    )


class TestMaxDrawdown:
    def test_no_drawdown(self):
        curve = [{"equity": 100}, {"equity": 110}, {"equity": 120}]
        assert _max_drawdown(curve) == 0.0

    def test_simple_drawdown(self):
        curve = [
            {"equity": 100}, {"equity": 120},
            {"equity": 90}, {"equity": 110},
        ]
        dd = _max_drawdown(curve)
        # Peak was 120, trough was 90 => -25%
        assert abs(dd - (-25.0)) < 0.01

    def test_empty_curve(self):
        assert _max_drawdown([]) == 0.0


class TestSharpeRatio:
    def test_zero_std_returns_zero(self):
        curve = [{"equity": 100}] * 10
        assert _sharpe_ratio(curve) == 0.0

    def test_positive_sharpe_for_uptrend(self):
        curve = [{"equity": 100 + i} for i in range(100)]
        sharpe = _sharpe_ratio(curve)
        assert sharpe > 0

    def test_short_curve(self):
        assert _sharpe_ratio([{"equity": 100}]) == 0.0


class TestAnnualizedReturn:
    def test_zero_for_single_point(self):
        curve = [{"equity": 100}]
        assert _annualized_return(curve, 100) == 0.0

    def test_positive_for_growth(self):
        curve = [{"equity": 100 + i * 0.5} for i in range(252)]
        result = _annualized_return(curve, 100)
        assert result > 0


class TestTradeStatistics:
    def test_no_trades(self):
        stats = _trade_statistics([])
        assert stats["total_trades"] == 0
        assert stats["win_rate"] == 0

    def test_all_winning_trades(self):
        trades = [
            _make_trade("AAPL", Side.BUY, 10, 100, 1, "2024-01-01"),
            _make_trade("AAPL", Side.SELL, 10, 120, 1, "2024-01-05"),
            _make_trade("AAPL", Side.BUY, 10, 110, 1, "2024-01-10"),
            _make_trade("AAPL", Side.SELL, 10, 130, 1, "2024-01-15"),
        ]
        stats = _trade_statistics(trades)
        assert stats["total_trades"] == 2
        assert stats["winning_trades"] == 2
        assert stats["losing_trades"] == 0
        assert stats["win_rate"] == 100.0

    def test_mixed_trades(self):
        trades = [
            _make_trade("AAPL", Side.BUY, 10, 100, 0, "2024-01-01"),
            _make_trade("AAPL", Side.SELL, 10, 110, 0, "2024-01-05"),
            _make_trade("AAPL", Side.BUY, 10, 120, 0, "2024-01-10"),
            _make_trade("AAPL", Side.SELL, 10, 100, 0, "2024-01-15"),
        ]
        stats = _trade_statistics(trades)
        assert stats["total_trades"] == 2
        assert stats["winning_trades"] == 1
        assert stats["losing_trades"] == 1
        assert stats["win_rate"] == 50.0


class TestConsecutiveStreaks:
    def test_all_wins(self):
        wins, losses = _consecutive_streaks([5.0, 3.0, 2.0])
        assert wins == 3
        assert losses == 0

    def test_all_losses(self):
        wins, losses = _consecutive_streaks([-2.0, -3.0, -1.0])
        assert wins == 0
        assert losses == 3

    def test_alternating(self):
        wins, losses = _consecutive_streaks([5.0, -2.0, 3.0, -1.0])
        assert wins == 1
        assert losses == 1


class TestCalculatePerformance:
    def test_empty_portfolio(self):
        portfolio = Portfolio(initial_capital=100_000)
        metrics = calculate_performance(portfolio)
        assert metrics.total_trades == 0
        assert metrics.total_return == 0

    def test_profitable_portfolio(self):
        portfolio = _make_portfolio_with_equity(
            [100_000, 101_000, 102_000, 103_000, 105_000],
            initial_capital=100_000,
        )
        portfolio.trades = [
            _make_trade("AAPL", Side.BUY, 10, 100, 1, "2024-01-01"),
            _make_trade("AAPL", Side.SELL, 10, 150, 1, "2024-01-03"),
        ]
        metrics = calculate_performance(portfolio)
        assert metrics.total_return > 0
        assert metrics.total_return_pct > 0
        assert metrics.total_trades == 1
