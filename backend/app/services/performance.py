"""Performance Calculator: compute trading performance metrics.

Takes trade records and equity curve from a completed backtest and
computes standard performance metrics (return, Sharpe, drawdown, etc.).
"""

import numpy as np
import pandas as pd

from app.models.schemas import PerformanceMetrics
from app.services.strategy import Portfolio, Side

TRADING_DAYS_PER_YEAR = 252


def calculate_performance(portfolio: Portfolio) -> PerformanceMetrics:
    """Compute all performance metrics from a completed backtest.

    Args:
        portfolio: Portfolio object after backtest completion, containing
                   trades and equity_history.

    Returns:
        PerformanceMetrics with all computed values.
    """
    equity_curve = portfolio.equity_history
    trades = portfolio.trades
    initial_capital = portfolio.initial_capital

    if not equity_curve:
        return _empty_metrics()

    final_equity = equity_curve[-1]["equity"]
    total_return = final_equity - initial_capital
    total_return_pct = (total_return / initial_capital) * 100

    annualized_return_pct = _annualized_return(equity_curve, initial_capital)
    max_drawdown_pct = _max_drawdown(equity_curve)
    sharpe = _sharpe_ratio(equity_curve)

    trade_stats = _trade_statistics(trades)

    return PerformanceMetrics(
        total_return=round(total_return, 2),
        total_return_pct=round(total_return_pct, 2),
        annualized_return_pct=round(annualized_return_pct, 2),
        max_drawdown_pct=round(max_drawdown_pct, 2),
        win_rate=round(trade_stats["win_rate"], 2),
        total_trades=trade_stats["total_trades"],
        winning_trades=trade_stats["winning_trades"],
        losing_trades=trade_stats["losing_trades"],
        sharpe_ratio=round(sharpe, 4),
        profit_factor=round(trade_stats["profit_factor"], 4),
        avg_trade_return_pct=round(trade_stats["avg_trade_return_pct"], 2),
        max_consecutive_wins=trade_stats["max_consecutive_wins"],
        max_consecutive_losses=trade_stats["max_consecutive_losses"],
    )


def _empty_metrics() -> PerformanceMetrics:
    """Return zeroed-out metrics when no data is available."""
    return PerformanceMetrics(
        total_return=0, total_return_pct=0, annualized_return_pct=0,
        max_drawdown_pct=0, win_rate=0, total_trades=0,
        winning_trades=0, losing_trades=0, sharpe_ratio=0,
        profit_factor=0, avg_trade_return_pct=0,
        max_consecutive_wins=0, max_consecutive_losses=0,
    )


def _annualized_return(equity_curve: list[dict],
                       initial_capital: float) -> float:
    """Calculate annualized return percentage.

    Args:
        equity_curve: List of {date, equity} dicts.
        initial_capital: Starting capital.

    Returns:
        Annualized return as a percentage.
    """
    if len(equity_curve) < 2:
        return 0.0

    final_equity = equity_curve[-1]["equity"]
    total_return_ratio = final_equity / initial_capital
    num_days = len(equity_curve)
    years = num_days / TRADING_DAYS_PER_YEAR

    if years <= 0 or total_return_ratio <= 0:
        return 0.0

    annualized = (total_return_ratio ** (1.0 / years)) - 1.0
    return annualized * 100


def _max_drawdown(equity_curve: list[dict]) -> float:
    """Calculate maximum drawdown percentage.

    Args:
        equity_curve: List of {date, equity} dicts.

    Returns:
        Maximum drawdown as a negative percentage (e.g., -15.5).
    """
    equities = [e["equity"] for e in equity_curve]
    if not equities:
        return 0.0

    peak = equities[0]
    max_dd = 0.0

    for equity in equities:
        if equity > peak:
            peak = equity
        drawdown = (equity - peak) / peak * 100 if peak > 0 else 0
        if drawdown < max_dd:
            max_dd = drawdown

    return max_dd


def _sharpe_ratio(equity_curve: list[dict],
                  risk_free_rate: float = 0.0) -> float:
    """Calculate annualized Sharpe ratio from equity curve.

    Args:
        equity_curve: List of {date, equity} dicts.
        risk_free_rate: Annual risk-free rate (default 0).

    Returns:
        Annualized Sharpe ratio.
    """
    if len(equity_curve) < 2:
        return 0.0

    equities = pd.Series([e["equity"] for e in equity_curve])
    daily_returns = equities.pct_change().dropna()

    if daily_returns.std() == 0:
        return 0.0

    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess_returns = daily_returns - daily_rf
    sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(
        TRADING_DAYS_PER_YEAR
    )
    return float(sharpe)


def _trade_statistics(trades: list) -> dict:
    """Compute win/loss statistics from matched trade pairs.

    Pairs BUY and SELL trades by symbol to compute round-trip P&L.

    Args:
        trades: List of Trade objects.

    Returns:
        Dict with trade statistics.
    """
    # Match buy/sell trades into round trips
    open_trades: dict[str, list] = {}
    round_trips: list[float] = []

    for trade in trades:
        if trade.side == Side.BUY:
            if trade.symbol not in open_trades:
                open_trades[trade.symbol] = []
            open_trades[trade.symbol].append(trade)
        elif trade.side == Side.SELL:
            if trade.symbol in open_trades and open_trades[trade.symbol]:
                buy_trade = open_trades[trade.symbol].pop(0)
                buy_cost = buy_trade.quantity * buy_trade.price + buy_trade.commission
                sell_revenue = trade.quantity * trade.price - trade.commission
                pnl_pct = ((sell_revenue - buy_cost) / buy_cost) * 100
                round_trips.append(pnl_pct)

    total_trades = len(round_trips)
    if total_trades == 0:
        return {
            "win_rate": 0, "total_trades": 0,
            "winning_trades": 0, "losing_trades": 0,
            "profit_factor": 0, "avg_trade_return_pct": 0,
            "max_consecutive_wins": 0, "max_consecutive_losses": 0,
        }

    winning = [r for r in round_trips if r > 0]
    losing = [r for r in round_trips if r <= 0]
    win_rate = (len(winning) / total_trades) * 100

    total_gains = sum(winning) if winning else 0
    total_losses = abs(sum(losing)) if losing else 0
    profit_factor = (total_gains / total_losses) if total_losses > 0 else float("inf")

    avg_return = sum(round_trips) / total_trades

    max_wins, max_losses = _consecutive_streaks(round_trips)

    return {
        "win_rate": win_rate,
        "total_trades": total_trades,
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "profit_factor": profit_factor,
        "avg_trade_return_pct": avg_return,
        "max_consecutive_wins": max_wins,
        "max_consecutive_losses": max_losses,
    }


def _consecutive_streaks(returns: list[float]) -> tuple[int, int]:
    """Find max consecutive wins and losses.

    Args:
        returns: List of round-trip return percentages.

    Returns:
        Tuple of (max_consecutive_wins, max_consecutive_losses).
    """
    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0

    for r in returns:
        if r > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        else:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)

    return max_wins, max_losses
