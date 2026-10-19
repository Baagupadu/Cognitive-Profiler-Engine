"""Application settings, loaded from environment variables or a local .env file."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ASYNC_POSTGRES_SCHEME = "postgresql+asyncpg://"
LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class Settings(BaseSettings):
    """Runtime configuration for the backend.

    Each field can be set with an environment variable of the same name
    (case-insensitive), for example ``DATABASE_URL`` or ``LOG_LEVEL``.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Cognitive Profiler Engine"
    log_level: str = "INFO"
    database_url: str
    db_connect_timeout_seconds: float = Field(default=5.0, gt=0)

    @field_validator("database_url")
    @classmethod
    def require_async_driver(cls, value: str) -> str:
        if not value.startswith(ASYNC_POSTGRES_SCHEME):
            raise ValueError(f"database_url must start with {ASYNC_POSTGRES_SCHEME}")
        return value

    @field_validator("log_level")
    @classmethod
    def normalise_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in LOG_LEVELS:
            raise ValueError(f"log_level must be one of {sorted(LOG_LEVELS)}")
        return level


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read once from the environment."""
    return Settings()
