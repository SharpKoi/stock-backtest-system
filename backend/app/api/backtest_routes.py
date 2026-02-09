"""API routes for backtest execution and result retrieval."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.schemas import BacktestRequest, BacktestResult, BacktestSummary
from app.services.backtest_service_async import BacktestService

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.post("", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest, db: AsyncSession = Depends(get_db)):
    """Run a new backtest with the specified parameters."""
    backtest_service = BacktestService(db)

    try:
        result = await backtest_service.run_backtest(request)
        await db.commit()
        return result
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Backtest execution failed: {exc}")


@router.get("", response_model=list[BacktestSummary])
async def list_backtests(db: AsyncSession = Depends(get_db)):
    """List all backtests with summary information."""
    backtest_service = BacktestService(db)
    backtests = await backtest_service.list_backtests()
    await db.commit()
    return backtests


@router.get("/{backtest_id}", response_model=BacktestResult)
async def get_backtest(backtest_id: int, db: AsyncSession = Depends(get_db)):
    """Get full backtest result by ID."""
    backtest_service = BacktestService(db)
    result = await backtest_service.get_backtest_result(backtest_id)
    await db.commit()

    if not result:
        raise HTTPException(status_code=404, detail=f"Backtest {backtest_id} not found")
    return result


@router.delete("/{backtest_id}")
async def delete_backtest(backtest_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a backtest and its associated data."""
    backtest_service = BacktestService(db)
    deleted = await backtest_service.delete_backtest(backtest_id)

    if not deleted:
        await db.rollback()
        raise HTTPException(status_code=404, detail=f"Backtest {backtest_id} not found")

    await db.commit()
    return {"message": f"Backtest {backtest_id} deleted"}
