"""Health endpoints, including the failure paths of the readiness check."""

from typing import Self

from fastapi import FastAPI
from httpx import AsyncClient

from app.api.health import get_engine


class FakeResult:
    def __init__(self, value: int | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> int | None:
        return self._value


class FakeConnection:
    def __init__(self, pgvector_available: bool) -> None:
        self._pgvector_available = pgvector_available

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def execute(self, statement: object) -> FakeResult:
        if "pg_available_extensions" in str(statement):
            return FakeResult(1 if self._pgvector_available else None)
        return FakeResult(1)


class FakeEngine:
    """Stands in for an AsyncEngine so readiness can be tested without PostgreSQL."""

    def __init__(self, *, reachable: bool = True, pgvector_available: bool = True) -> None:
        self._reachable = reachable
        self._pgvector_available = pgvector_available

    def connect(self) -> FakeConnection:
        if not self._reachable:
            raise OSError("connection refused")
        return FakeConnection(self._pgvector_available)


async def test_liveness_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_is_ready_when_database_and_pgvector_are_available(
    app: FastAPI, client: AsyncClient
) -> None:
    app.dependency_overrides[get_engine] = lambda: FakeEngine()

    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": True, "pgvector_available": True}


async def test_readiness_returns_503_when_pgvector_is_missing(
    app: FastAPI, client: AsyncClient
) -> None:
    app.dependency_overrides[get_engine] = lambda: FakeEngine(pgvector_available=False)

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": True,
        "pgvector_available": False,
    }


async def test_readiness_returns_503_when_database_is_unreachable(
    app: FastAPI, client: AsyncClient
) -> None:
    app.dependency_overrides[get_engine] = lambda: FakeEngine(reachable=False)

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": False,
        "pgvector_available": False,
    }
