import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/jobs_lab"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    database_url: str
    redis_url: str
    otel_enabled: bool
    otel_exporter_otlp_endpoint: str | None
    worker_poll_interval_seconds: float


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("JOBS_LAB_APP_NAME", "Jobs Lab"),
        environment=os.getenv("JOBS_LAB_ENV", "local"),
        database_url=normalize_database_url(
            os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        ),
        redis_url=os.getenv("REDIS_URL", DEFAULT_REDIS_URL),
        otel_enabled=parse_bool(os.getenv("OTEL_ENABLED", "false")),
        otel_exporter_otlp_endpoint=optional_env("OTEL_EXPORTER_OTLP_ENDPOINT"),
        worker_poll_interval_seconds=float(
            os.getenv("JOBS_LAB_WORKER_POLL_INTERVAL_SECONDS", "1")
        ),
    )


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return database_url


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return value
