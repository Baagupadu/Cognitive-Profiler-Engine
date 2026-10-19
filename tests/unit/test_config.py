"""Settings validation (NFR-03: validate configuration input)."""

import pytest
from pydantic import ValidationError

from app.config import Settings

VALID_URL = "postgresql+asyncpg://cpe:cpe@localhost:5432/cpe"


def test_rejects_database_url_without_async_driver() -> None:
    with pytest.raises(ValidationError, match=r"postgresql\+asyncpg"):
        Settings(database_url="postgresql://cpe:cpe@localhost:5432/cpe")


def test_normalises_log_level_to_upper_case() -> None:
    settings = Settings(database_url=VALID_URL, log_level="debug")

    assert settings.log_level == "DEBUG"


def test_rejects_unknown_log_level() -> None:
    with pytest.raises(ValidationError, match="log_level"):
        Settings(database_url=VALID_URL, log_level="LOUD")
