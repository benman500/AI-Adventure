"""Application settings via pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the application."""

    model_config = SettingsConfigDict(
        env_prefix="AI_ADVENTURE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Adventure"
    debug: bool = False
    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{(_PROJECT_ROOT / 'saves' / 'game.db').as_posix()}"
    )
    narrator_backend: str = "stub"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
