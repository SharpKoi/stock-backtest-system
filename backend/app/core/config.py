"""Application configuration settings.

Uses pydantic-settings for environment-based configuration.
Supports both local (SQLite) and cloud (PostgreSQL) deployments.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["local", "development", "staging", "production"] = "local"

    # Project paths
    project_root: Path = Path(__file__).parent.parent.parent

    # Database settings
    database_type: Literal["sqlite", "postgresql"] = "sqlite"
    database_url: str = "sqlite:///./data/backtest.db"

    # For SQLite (local development)
    sqlite_database_path: Path = project_root / "data" / "backtest.db"

    # For PostgreSQL (cloud deployment)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_db: str = "backtest"

    # Redis settings (for future task queue)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: str = "redis://localhost:6379/0"

    # Default backtest settings
    default_initial_capital: float = 100_000.0
    default_commission_rate: float = 0.001  # 0.1% per trade

    # Data download settings
    default_data_period: str = "5y"

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # Strategy and workspace paths
    strategies_dir: Path = project_root / "strategies"

    # User workspace settings (for local development)
    workspace_dir: Path = Path.home() / ".vici-backtest"

    # Cloud storage settings (for cloud deployment)
    s3_bucket: str = ""
    s3_region: str = "us-east-1"

    @property
    def database_path(self) -> Path:
        """Get the SQLite database path (for local development)."""
        return self.sqlite_database_path

    @property
    def postgres_database_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def get_database_url(self) -> str:
        """Get the appropriate database URL based on database_type."""
        if self.database_type == "postgresql":
            return self.postgres_database_url
        return f"sqlite:///{self.sqlite_database_path}"


# Global settings instance
settings = Settings()

# Legacy constants for backward compatibility
PROJECT_ROOT = settings.project_root
DATABASE_PATH = settings.database_path
STRATEGIES_DIR = settings.strategies_dir
DEFAULT_INITIAL_CAPITAL = settings.default_initial_capital
DEFAULT_COMMISSION_RATE = settings.default_commission_rate
DEFAULT_DATA_PERIOD = settings.default_data_period
API_HOST = settings.api_host
API_PORT = settings.api_port
CORS_ORIGINS = settings.cors_origins
