"""API routes for strategy management."""

from fastapi import APIRouter

from app.services.strategy_loader import list_strategy_info

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("")
def list_strategies():
    """List all available strategies with metadata."""
    return list_strategy_info()
