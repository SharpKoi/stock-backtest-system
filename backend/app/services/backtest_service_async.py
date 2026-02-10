"""Async Backtest Service: orchestrates running backtests and storing results.

This is the async SQLAlchemy version that replaces the sync sqlite3 implementation.
"""

import json
import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Backtest, BacktestResult, Trade
from app.models.schemas import (
    BacktestRequest,
    BacktestResult as BacktestResultSchema,
    BacktestSummary,
    PerformanceMetrics,
    TradeRecord,
)
from app.services.data_manager_async import DataManager
from app.services.engine import BacktestEngine
from app.services.performance import calculate_performance
from app.services.report_generator import generate_console_report, generate_html_report
from app.services.strategy_loader import get_strategy_class

logger = logging.getLogger(__name__)


class BacktestService:
    """High-level async service for running and managing backtests."""

    def __init__(self, db_session: AsyncSession):
        """Initialize with async database session.

        Args:
            db_session: SQLAlchemy async session.
        """
        self.db = db_session
        self._data_manager = DataManager(db_session)

    async def run_backtest(self, request: BacktestRequest, user_id: int | None = None) -> BacktestResultSchema:
        """Execute a complete backtest workflow.

        1. Load strategy class
        2. Load OHLCV data for all symbols
        3. Run the backtest engine
        4. Calculate performance metrics
        5. Store results in database
        6. Generate reports

        Args:
            request: BacktestRequest with strategy, symbols, dates, etc.
            user_id: Optional user ID to associate backtest with (for auth)

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
            df = await self._data_manager.get_ohlcv(symbol, request.start_date, request.end_date)
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
        backtest_id = await self._store_backtest(request, portfolio, metrics, user_id)

        # 6. Generate reports
        console_report = generate_console_report(
            metrics, portfolio, strategy.name, request.symbols
        )
        logger.info("\n%s", console_report)

        generate_html_report(
            metrics, portfolio, strategy.name, request.symbols, backtest_id=backtest_id
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

        return BacktestResultSchema(
            backtest_id=backtest_id,
            name=request.name,
            strategy_name=strategy.name,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            final_equity=(
                portfolio.equity_history[-1]["equity"]
                if portfolio.equity_history
                else request.initial_capital
            ),
            metrics=metrics,
            trades=trades,
            equity_curve=portfolio.equity_history,
        )

    async def _store_backtest(
        self, request: BacktestRequest, portfolio, metrics: PerformanceMetrics, user_id: int | None = None
    ) -> int:
        """Persist backtest metadata, trades, and results to database.

        Args:
            request: The original backtest request.
            portfolio: The portfolio after backtest completion.
            metrics: Computed performance metrics.
            user_id: Optional user ID to associate backtest with

        Returns:
            The backtest ID.
        """
        # Create backtest record
        backtest = Backtest(
            user_id=user_id,
            name=request.name,
            strategy_name=request.strategy_name,
            symbols=json.dumps(request.symbols),
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            status="completed",
        )
        self.db.add(backtest)
        await self.db.flush()  # Get backtest.id

        # Store trades
        for trade in portfolio.trades:
            trade_record = Trade(
                backtest_id=backtest.id,
                symbol=trade.symbol,
                side=trade.side.value,
                quantity=trade.quantity,
                price=trade.price,
                commission=trade.commission,
                date=trade.date,
            )
            self.db.add(trade_record)

        # Store results
        result_record = BacktestResult(
            backtest_id=backtest.id,
            metrics_json=metrics.model_dump_json(),
            equity_curve_json=json.dumps(portfolio.equity_history),
        )
        self.db.add(result_record)

        await self.db.flush()
        return backtest.id

    async def get_backtest_result(self, backtest_id: int, user_id: int | None = None) -> BacktestResultSchema | None:
        """Retrieve a stored backtest result by ID.

        Args:
            backtest_id: The backtest ID.
            user_id: Optional user ID to filter by (ensures user owns the backtest)

        Returns:
            BacktestResult if found, None otherwise.
        """
        # Load backtest with relationships
        query = (
            select(Backtest)
            .where(Backtest.id == backtest_id)
            .options(selectinload(Backtest.trades), selectinload(Backtest.result))
        )

        # Filter by user_id if provided
        if user_id is not None:
            query = query.where(Backtest.user_id == user_id)

        result = await self.db.execute(query)
        backtest = result.scalar_one_or_none()

        if not backtest or not backtest.result:
            return None

        # Parse metrics and equity curve
        metrics = PerformanceMetrics.model_validate_json(backtest.result.metrics_json)
        equity_curve = json.loads(backtest.result.equity_curve_json)

        # Convert trades
        trades = [
            TradeRecord(
                id=t.id,
                backtest_id=t.backtest_id,
                symbol=t.symbol,
                side=t.side,
                quantity=t.quantity,
                price=t.price,
                commission=t.commission,
                date=t.date,
            )
            for t in backtest.trades
        ]

        symbols = json.loads(backtest.symbols)
        final_equity = equity_curve[-1]["equity"] if equity_curve else backtest.initial_capital

        return BacktestResultSchema(
            backtest_id=backtest_id,
            name=backtest.name,
            strategy_name=backtest.strategy_name,
            symbols=symbols,
            start_date=backtest.start_date,
            end_date=backtest.end_date,
            initial_capital=backtest.initial_capital,
            final_equity=final_equity,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
        )

    async def list_backtests(self, user_id: int | None = None) -> list[BacktestSummary]:
        """List all backtests with summary information.

        Args:
            user_id: Optional user ID to filter backtests by owner

        Returns:
            List of BacktestSummary objects.
        """
        query = select(Backtest).order_by(Backtest.created_at.desc())

        # Filter by user_id if provided
        if user_id is not None:
            query = query.where(Backtest.user_id == user_id)

        result = await self.db.execute(query)
        backtests = result.scalars().all()

        return [
            BacktestSummary(
                id=bt.id,
                name=bt.name,
                strategy_name=bt.strategy_name,
                symbols=json.loads(bt.symbols),
                start_date=bt.start_date,
                end_date=bt.end_date,
                initial_capital=bt.initial_capital,
                status=bt.status,
                created_at=bt.created_at.isoformat(),
            )
            for bt in backtests
        ]

    async def delete_backtest(self, backtest_id: int, user_id: int | None = None) -> bool:
        """Delete a backtest and its associated data.

        Args:
            backtest_id: The backtest ID to delete.
            user_id: Optional user ID to verify ownership

        Returns:
            True if deleted, False if not found.
        """
        query = select(Backtest).where(Backtest.id == backtest_id)

        # Filter by user_id if provided
        if user_id is not None:
            query = query.where(Backtest.user_id == user_id)

        result = await self.db.execute(query)
        backtest = result.scalar_one_or_none()

        if not backtest:
            return False

        # Delete backtest (cascades to trades and results)
        await self.db.delete(backtest)
        await self.db.flush()
        return True
