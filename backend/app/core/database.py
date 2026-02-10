"""Database initialization and migration management.

This module provides async database initialization using Alembic migrations.
Replaces the old sync SQLite-only implementation with async support for both
SQLite and PostgreSQL.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import settings
from app.db import engine

logger = logging.getLogger(__name__)


async def initialize_database() -> None:
    """Initialize database by running Alembic migrations.

    This function:
    1. Ensures the database directory exists (for SQLite)
    2. Runs Alembic migrations to create/update tables
    3. For SQLite, enables WAL mode and foreign keys

    For production deployments, you should run migrations separately
    using `alembic upgrade head` in your deployment pipeline.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    # Ensure database directory exists for SQLite
    if settings.database_type == "sqlite":
        db_path = settings.sqlite_database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"SQLite database path: {db_path}")

        # Configure SQLite-specific settings
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            logger.info("SQLite pragmas configured (WAL mode, foreign keys enabled)")

    # Run Alembic migrations in a thread pool (since Alembic isn't fully async)
    try:

        def run_migrations():
            alembic_cfg = get_alembic_config()
            command.upgrade(alembic_cfg, "head")

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, run_migrations)

        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}")
        # For initial setup, fall back to creating tables directly
        logger.warning("Attempting to create tables directly using SQLAlchemy...")
        from app.db import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully")


def get_alembic_config() -> Config:
    """Get Alembic configuration.

    Returns:
        Alembic Config object pointing to the alembic.ini file.
    """
    # Path to alembic.ini (should be in backend/ directory)
    backend_dir = Path(__file__).parent.parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"

    if not alembic_ini_path.exists():
        raise FileNotFoundError(
            f"alembic.ini not found at {alembic_ini_path}. "
            "Run 'alembic init alembic' to initialize Alembic."
        )

    alembic_cfg = Config(str(alembic_ini_path))
    return alembic_cfg


async def check_database_connection() -> bool:
    """Check if database connection is working.

    Returns:
        True if connection successful, False otherwise.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
