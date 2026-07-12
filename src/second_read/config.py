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

    # Groq chat models (free tier). Embeddings run locally via sentence-transformers.
    model_ingest: str = "llama-3.3-70b-versatile"
    model_connect: str = "llama-3.3-70b-versatile"
    model_ping: str = "llama-3.3-70b-versatile"
    model_converse: str = "llama-3.3-70b-versatile"
    model_embed: str = "all-MiniLM-L6-v2"

    database_url: str = "sqlite:///./data/second_read.db"

    quiet_hours_start: int = 9
    quiet_hours_end: int = 21
    max_pings_per_day: int = 2
    ping_check_interval_minutes: int = 45

    def ensure_data_dir(self) -> None:
        if self.database_url.startswith("sqlite:///"):
            path = self.database_url.removeprefix("sqlite:///")
            Path(path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
