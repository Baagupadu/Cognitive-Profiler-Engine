"""Integration tests that need PostgreSQL with pgvector (``docker compose up -d db``)."""

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.integration


def database_settings() -> Settings:
    try:
        return Settings()
    except ValidationError:
        pytest.skip("DATABASE_URL is not configured (see .env.example)")


async def test_readiness_against_real_database() -> None:
    app = create_app(database_settings())
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")
    finally:
        await app.state.engine.dispose()

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": True, "pgvector_available": True}
