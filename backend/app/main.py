"""FastAPI application factory.

Run locally with: uvicorn app.main:create_app --factory --reload
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import health
from app.config import Settings, get_settings
from app.db.engine import create_engine
from app.observability import CorrelationIdMiddleware, configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Tests pass their own settings; otherwise read the environment."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        logger.info("application started")
        yield
        await application.state.engine.dispose()
        logger.info("application stopped")

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = create_engine(settings.database_url, settings.db_connect_timeout_seconds)
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(health.router)
    return app
