"""Shared fixtures. Unit tests never open a real database connection."""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app

# Nothing listens on port 1, so any accidental real connection fails fast.
UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://cpe:cpe@127.0.0.1:1/cpe"


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url=UNREACHABLE_DATABASE_URL, log_level="WARNING")


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    yield application
    await application.state.engine.dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
