"""FastAPI application entry point.

Configures CORS, registers API routers, and initializes the database.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.backtest_routes import router as backtest_router
from app.api.data_routes import router as data_router
from app.api.indicator_routes import router as indicator_router
from app.api.strategy_routes import router as strategy_router
from app.core.config import CORS_ORIGINS, STRATEGIES_DIR
from app.core.database import initialize_database
from app.services.indicator_loader import discover_indicators
from app.services.indicators import register_custom_indicator
from app.services.workspace import (
    ensure_indicators_dir_exists,
    initialize_workspace_with_examples,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    await initialize_database()
    logger.info("Database initialized")

    # Initialize user workspace with example strategies
    initialize_workspace_with_examples(STRATEGIES_DIR)
    logger.info("User workspace initialized")

    # Load custom indicators from user workspace
    ensure_indicators_dir_exists()
    custom_indicators = discover_indicators()
    for name, cls in custom_indicators.items():
        register_custom_indicator(name, cls)
    logger.info("Loaded %d custom indicators", len(custom_indicators))

    yield


app = FastAPI(
    title="Stock Backtesting System",
    description="A backtesting platform for US stock trading strategies",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_router)
app.include_router(strategy_router)
app.include_router(indicator_router)
app.include_router(backtest_router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
