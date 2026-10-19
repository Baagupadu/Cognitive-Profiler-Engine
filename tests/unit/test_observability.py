"""Correlation IDs and JSON logging (NFR-07)."""

import json
import logging

import pytest
from httpx import AsyncClient

from app.observability import CORRELATION_ID_HEADER, JsonFormatter, correlation_id_var


async def test_generates_correlation_id_when_header_is_missing(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert len(response.headers[CORRELATION_ID_HEADER]) == 32


async def test_reuses_well_formed_incoming_correlation_id(client: AsyncClient) -> None:
    response = await client.get("/health", headers={CORRELATION_ID_HEADER: "req-123"})

    assert response.headers[CORRELATION_ID_HEADER] == "req-123"


async def test_replaces_malformed_incoming_correlation_id(client: AsyncClient) -> None:
    malformed = "not valid; drop table"

    response = await client.get("/health", headers={CORRELATION_ID_HEADER: malformed})

    assert response.headers[CORRELATION_ID_HEADER] != malformed
    assert len(response.headers[CORRELATION_ID_HEADER]) == 32


async def test_logs_each_completed_request(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.observability"):
        await client.get("/health")

    record = next(r for r in caplog.records if r.getMessage() == "request completed")
    fields = record.__dict__["fields"]
    assert fields["method"] == "GET"
    assert fields["path"] == "/health"
    assert fields["status"] == 200
    assert fields["duration_ms"] >= 0


def test_json_formatter_includes_correlation_id_and_extra_fields() -> None:
    record = logging.makeLogRecord(
        {
            "name": "test",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "hello %s",
            "args": ("world",),
            "fields": {"node": "router"},
        }
    )
    token = correlation_id_var.set("req-1")
    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        correlation_id_var.reset(token)

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["correlation_id"] == "req-1"
    assert payload["node"] == "router"
