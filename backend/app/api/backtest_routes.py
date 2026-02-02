"""API routes for backtest execution and result retrieval."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import BacktestRequest, BacktestResult, BacktestSummary
from app.services.backtest_service import BacktestService

router = APIRouter(prefix="/api/backtests", tags=["backtests"])

backtest_service = BacktestService()


@router.post("", response_model=BacktestResult)
def run_backtest(request: BacktestRequest):
    """Run a new backtest with the specified parameters."""
    try:
        result = backtest_service.run_backtest(request)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Backtest execution failed: {exc}"
        )


@router.get("", response_model=list[BacktestSummary])
def list_backtests():
    """List all backtests with summary information."""
    return backtest_service.list_backtests()


@router.get("/{backtest_id}", response_model=BacktestResult)
def get_backtest(backtest_id: int):
    """Get full backtest result by ID."""
    result = backtest_service.get_backtest_result(backtest_id)
    if not result:
        raise HTTPException(
            status_code=404, detail=f"Backtest {backtest_id} not found"
        )
    return result


@router.delete("/{backtest_id}")
def delete_backtest(backtest_id: int):
    """Delete a backtest and its associated data."""
    deleted = backtest_service.delete_backtest(backtest_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Backtest {backtest_id} not found"
        )
    return {"message": f"Backtest {backtest_id} deleted"}
