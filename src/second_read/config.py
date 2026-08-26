from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str
    telegram_user_id: int

    groq_api_key: str

    model_ingest: str = "openai/gpt-oss-120b"

    database_url: str = "sqlite:///./data/second_read.db"

    digest_hour: int = 8

    site_url: str = ""

    def ensure_data_dir(self) -> None:
        if self.database_url.startswith("sqlite:///"):
            path = self.database_url.removeprefix("sqlite:///")
            Path(path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
