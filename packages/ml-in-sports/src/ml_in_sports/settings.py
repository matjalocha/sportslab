"""Centralized configuration for ml_in_sports.

All configurable paths, thresholds, and external service settings live here.
Values come from environment variables with the ``ML_IN_SPORTS_`` prefix,
or fall back to sensible defaults for local development.

Usage::

    from ml_in_sports.settings import get_settings

    settings = get_settings()
    db_path = settings.db_path
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Env var prefix: ``ML_IN_SPORTS_``

    Example::

        ML_IN_SPORTS_DB_PATH=data/football.db
    """

    model_config = {"env_prefix": "ML_IN_SPORTS_"}

    db_path: Path = Path("data/football.db")
    fifa_data_dir: Path = Path("data/fifa")
    pinnacle_odds_dir: Path = Path("data/odds")
    log_level: str = "INFO"
    log_json: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance.

    Call this instead of ``Settings()`` directly to avoid re-parsing
    environment variables on every access.
    """
    return Settings()
