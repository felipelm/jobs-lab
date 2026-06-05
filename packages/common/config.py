import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("JOBS_LAB_APP_NAME", "Jobs Lab"),
        environment=os.getenv("JOBS_LAB_ENV", "local"),
    )

