"""Backtest Service: orchestrates running backtests and storing results.

Coordinates the DataManager, StrategyLoader, BacktestEngine,
PerformanceCalculator, and ReportGenerator into a single workflow.
"""

import json
import logging
import sqlite3
from pathlib import Path

from app.core.config import DATABASE_PATH
from app.core.database import get_connection
from app.models.schemas import (
    BacktestRequest,
    BacktestResult,
    BacktestSummary,
    PerformanceMetrics,
    TradeRecord,
)
from app.services.data_manager import DataManager
from app.services.engine import BacktestEngine
from app.services.performance import calculate_performance
from app.services.report_generator import generate_console_report, generate_html_report
from app.services.strategy_loader import get_strategy_class

logger = logging.getLogger(__name__)


class BacktestService:
    """High-level service for running and managing backtests."""

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or DATABASE_PATH
        self._data_manager = DataManager(self._db_path)

    def _get_conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def run_backtest(self, request: BacktestRequest) -> BacktestResult:
        """Execute a complete backtest workflow.

        1. Load strategy class
        2. Load OHLCV data for all symbols
        3. Run the backtest engine
        4. Calculate performance metrics
        5. Store results in database
        6. Generate reports

        Args:
            request: BacktestRequest with strategy, symbols, dates, etc.

        Returns:
            BacktestResult with metrics, trades, and equity curve.

        Raises:
            ValueError: If strategy not found or data missing.
        """
        # 1. Load strategy
        strategy_class = get_strategy_class(request.strategy_name)
        if not strategy_class:
            raise ValueError(
                f"Strategy '{request.strategy_name}' not found. "
                f"Ensure the file exists in the strategies directory."
            )

        strategy = strategy_class(params=request.strategy_params)

        # 2. Load data
        data = {}
        for symbol in request.symbols:
            df = self._data_manager.get_ohlcv(
                symbol, request.start_date, request.end_date
            )
            if df.empty:
                raise ValueError(
                    f"No data found for '{symbol}' in range "
                    f"{request.start_date} to {request.end_date}. "
                    f"Download the data first."
                )
            data[symbol] = df

        # 3. Run engine
        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
        )
        portfolio = engine.run(data)

        # 4. Calculate metrics
        metrics = calculate_performance(portfolio)

        # 5. Store results in database
        backtest_id = self._store_backtest(request, portfolio, metrics)

        # 6. Generate reports
        console_report = generate_console_report(
            metrics, portfolio, strategy.name, request.symbols
        )
        logger.info("\n%s", console_report)

        generate_html_report(
            metrics, portfolio, strategy.name, request.symbols,
            backtest_id=backtest_id
        )

        # 7. Build response
        trades = [
            TradeRecord(
                backtest_id=backtest_id,
                symbol=t.symbol,
                side=t.side.value,
                quantity=t.quantity,
                price=t.price,
                commission=t.commission,
                date=t.date,
            )
            for t in portfolio.trades
        ]

        return BacktestResult(
            backtest_id=backtest_id,
            name=request.name,
            strategy_name=strategy.name,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            final_equity=(
                portfolio.equity_history[-1]["equity"] if portfolio.equity_history else request.initial_capital
            ),
            metrics=metrics,
            trades=trades,
            equity_curve=portfolio.equity_history,
        )

    def _store_backtest(self, request: BacktestRequest,
                        portfolio, metrics: PerformanceMetrics) -> int:
        """Persist backtest metadata, trades, and results to database.

        Args:
            request: The original backtest request.
            portfolio: The portfolio after backtest completion.
            metrics: Computed performance metrics.

        Returns:
            The backtest ID.
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO backtests "
                "(name, strategy_name, symbols, start_date, end_date, "
                "initial_capital, commission_rate, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    request.name, request.strategy_name,
                    json.dumps(request.symbols),
                    request.start_date, request.end_date,
                    request.initial_capital, request.commission_rate,
                    "completed"
                )
            )
            backtest_id = cursor.lastrowid

            # Store trades
            for trade in portfolio.trades:
                conn.execute(
                    "INSERT INTO trades "
                    "(backtest_id, symbol, side, quantity, price, commission, date) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        backtest_id, trade.symbol, trade.side.value,
                        trade.quantity, trade.price, trade.commission,
                        trade.date
                    )
                )

            # Store results
            conn.execute(
                "INSERT INTO backtest_results "
                "(backtest_id, metrics_json, equity_curve_json) "
                "VALUES (?, ?, ?)",
                (
                    backtest_id,
                    metrics.model_dump_json(),
                    json.dumps(portfolio.equity_history),
                )
            )

            conn.commit()
            return backtest_id
        finally:
            conn.close()

    def get_backtest_result(self, backtest_id: int) -> BacktestResult | None:
        """Retrieve a stored backtest result by ID.

        Args:
            backtest_id: The backtest ID.

        Returns:
            BacktestResult if found, None otherwise.
        """
        conn = self._get_conn()
        try:
            bt = conn.execute(
                "SELECT * FROM backtests WHERE id = ?", (backtest_id,)
            ).fetchone()
            if not bt:
                return None

            result_row = conn.execute(
                "SELECT * FROM backtest_results WHERE backtest_id = ?",
                (backtest_id,)
            ).fetchone()

            trade_rows = conn.execute(
                "SELECT * FROM trades WHERE backtest_id = ? ORDER BY date",
                (backtest_id,)
            ).fetchall()

            metrics = PerformanceMetrics.model_validate_json(
                result_row["metrics_json"]
            )
            equity_curve = json.loads(result_row["equity_curve_json"])

            trades = [
                TradeRecord(
                    id=r["id"], backtest_id=r["backtest_id"],
                    symbol=r["symbol"], side=r["side"],
                    quantity=r["quantity"], price=r["price"],
                    commission=r["commission"], date=r["date"],
                )
                for r in trade_rows
            ]

            symbols = json.loads(bt["symbols"])
            final_equity = equity_curve[-1]["equity"] if equity_curve else bt["initial_capital"]

            return BacktestResult(
                backtest_id=backtest_id,
                name=bt["name"],
                strategy_name=bt["strategy_name"],
                symbols=symbols,
                start_date=bt["start_date"],
                end_date=bt["end_date"],
                initial_capital=bt["initial_capital"],
                final_equity=final_equity,
                metrics=metrics,
                trades=trades,
                equity_curve=equity_curve,
            )
        finally:
            conn.close()

    def list_backtests(self) -> list[BacktestSummary]:
        """List all backtests with summary information.

        Returns:
            List of BacktestSummary objects.
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM backtests ORDER BY created_at DESC"
            ).fetchall()
            return [
                BacktestSummary(
                    id=r["id"], name=r["name"],
                    strategy_name=r["strategy_name"],
                    symbols=json.loads(r["symbols"]),
                    start_date=r["start_date"], end_date=r["end_date"],
                    initial_capital=r["initial_capital"],
                    status=r["status"], created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def delete_backtest(self, backtest_id: int) -> bool:
        """Delete a backtest and its associated data.

        Args:
            backtest_id: The backtest ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id FROM backtests WHERE id = ?", (backtest_id,)
            ).fetchone()
            if not row:
                return False

            conn.execute(
                "DELETE FROM backtest_results WHERE backtest_id = ?",
                (backtest_id,)
            )
            conn.execute(
                "DELETE FROM trades WHERE backtest_id = ?", (backtest_id,)
            )
            conn.execute(
                "DELETE FROM backtests WHERE id = ?", (backtest_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()
