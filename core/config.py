from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    env: Literal["production", "development", "test"] = "production"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    bot_token: str = Field(..., min_length=10)
    owner_id: int
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")
    log_channel_id: int | None = None

    database_url: str = "sqlite+aiosqlite:///./data/bot.db"

    fernet_key: str | None = None

    tg_api_id: int | None = None
    tg_api_hash: str | None = None
    userbot_phone: str | None = None
    backup_userbot_phone: str | None = None

    health_host: str = "0.0.0.0"
    health_port: int = 8080

    @computed_field  # type: ignore[prop-decorator]
    @property
    def admin_ids(self) -> list[int]:
        raw = (self.admin_ids_raw or "").strip()
        if not raw:
            return []
        return [int(x.strip()) for x in raw.split(",") if x.strip()]

    @property
    def is_dev(self) -> bool:
        return self.env == "development"

    @property
    def all_admin_ids(self) -> set[int]:
        return {self.owner_id, *self.admin_ids}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()
