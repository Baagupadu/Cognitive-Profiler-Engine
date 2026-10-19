"""Liveness and readiness endpoints."""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: bool
    pgvector_available: bool


def get_engine(request: Request) -> AsyncEngine:
    """Return the application's database engine. Tests override this dependency."""
    engine: AsyncEngine = request.app.state.engine
    return engine


@router.get("")
async def liveness() -> LivenessResponse:
    """The process is up and serving requests."""
    return LivenessResponse(status="ok")


@router.get(
    "/ready",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness(
    response: Response,
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> ReadinessResponse:
    """The database is reachable and the pgvector extension is available to install."""
    database = False
    pgvector_available = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            database = True
            result = await connection.execute(
                text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
            )
            pgvector_available = result.scalar_one_or_none() is not None
    except Exception:
        # Any failure here simply means "not ready"; the details go to the log.
        logger.warning("readiness check failed", exc_info=True)

    ready = database and pgvector_available
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        database=database,
        pgvector_available=pgvector_available,
    )
