"""Alembic environment: runs migrations with the async engine.

The database URL is taken from ``config.attributes["database_url"]`` when set (tests do this),
otherwise from the application settings (``DATABASE_URL``).
"""

import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings
from app.db.models import Base

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    url = config.attributes.get("database_url")
    return str(url) if url else Settings().database_url


def run_migrations_offline() -> None:
    """Print the SQL instead of running it (``alembic upgrade head --sql``)."""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(database_url())
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
