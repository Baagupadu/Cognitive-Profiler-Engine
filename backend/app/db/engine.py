"""Async SQLAlchemy engine for PostgreSQL (asyncpg driver)."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine(database_url: str, connect_timeout_seconds: float) -> AsyncEngine:
    """Create the engine. No connection is opened until the engine is first used."""
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"timeout": connect_timeout_seconds},
    )
