# config.py
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KOWALSKI_", env_file=".env")

    database_url: str = f"sqlite:///{BASE_DIR / 'kowalski.db'}"
    upload_dir: Path = BASE_DIR / "uploaded_charts"
    max_chart_bytes: int = 10 * 1024 * 1024
    max_charts_per_upload: int = 10
    log_level: str = "INFO"
    sql_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
