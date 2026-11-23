"""Application settings.

All values come from environment variables (prefix ``DATOSABIERTOS_``) or a local
``.env`` file. No secret ever has a code-level default in a production path.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DATOSABIERTOS_",
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+psycopg://datosabiertos:datosabiertos@localhost:55437/datosabiertos"
    )
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=50)
    database_echo: bool = False

    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3100"

    storage_root: Path = Path("./data/storage")

    ingestion_user_agent: str = (
        "DatosAbiertosAR/0.1 (+https://github.com/Lolisticos/datosabiertos-ar)"
    )
    ingestion_max_download_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)
    ingestion_request_timeout_seconds: float = Field(default=30.0, gt=0)
    ingestion_requests_per_second: float = Field(default=2.0, ge=0)
    ingestion_retry_attempts: int = Field(default=3, ge=1, le=10)

    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=500)

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in allowed:
            raise ValueError(f"log level must be one of {sorted(allowed)}")
        return level

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
