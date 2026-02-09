"""Database engine and session management.

Provides async database engine and session factory for FastAPI dependency injection.
Supports both SQLite (dev) and PostgreSQL (prod).
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base


def get_database_url() -> str:
    """Get the appropriate database URL for async operations.

    Converts database URLs to use async drivers:
    - sqlite:/// -> sqlite+aiosqlite:///
    - postgresql:// -> postgresql+asyncpg://

    Returns:
        Async-compatible database URL string.
    """
    db_url = settings.get_database_url()

    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    elif db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        # Assume it's already async-compatible
        return db_url


# Create async engine
engine = create_async_engine(
    get_database_url(),
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Test connections before using them
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get async database session.

    Yields:
        AsyncSession instance that automatically closes after request.

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database by creating all tables.

    This creates tables using SQLAlchemy metadata.
    For production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
