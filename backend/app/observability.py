"""Structured JSON logging with a correlation ID per request (NFR-07)."""

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CORRELATION_ID_HEADER = "X-Correlation-ID"
_VALID_CORRELATION_ID = re.compile(r"[A-Za-z0-9-]{1,64}")

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

logger = logging.getLogger(__name__)


class JsonFormatter(logging.Formatter):
    """Formats each record as one JSON object that includes the current correlation ID.

    Extra structured data can be attached with ``logger.info("...", extra={"fields": {...}})``.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }
        fields = record.__dict__.get("fields")
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    """Write all log records to stderr as JSON lines. Safe to call more than once."""
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)


class CorrelationIdMiddleware:
    """Gives every HTTP request a correlation ID and logs the request when it completes.

    A well-formed incoming ``X-Correlation-ID`` header is reused. Anything else is
    replaced with a random ID, so untrusted header values never reach the logs.
    The ID is returned in the response headers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(CORRELATION_ID_HEADER)
        if incoming is not None and _VALID_CORRELATION_ID.fullmatch(incoming):
            correlation_id = incoming
        else:
            correlation_id = uuid.uuid4().hex
        token = correlation_id_var.set(correlation_id)
        status_code = 500
        started = time.perf_counter()

        async def send_with_correlation_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append(CORRELATION_ID_HEADER, correlation_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation_id)
        finally:
            logger.info(
                "request completed",
                extra={
                    "fields": {
                        "method": scope["method"],
                        "path": scope["path"],
                        "status": status_code,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    }
                },
            )
            correlation_id_var.reset(token)
