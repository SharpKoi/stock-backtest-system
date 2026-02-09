"""Application configuration settings."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "backtest.db"
STRATEGIES_DIR = PROJECT_ROOT / "strategies"

# Default backtest settings
DEFAULT_INITIAL_CAPITAL = 100_000.0
DEFAULT_COMMISSION_RATE = 0.001  # 0.1% per trade

# Data download settings
DEFAULT_DATA_PERIOD = "5y"

# API settings
API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]
