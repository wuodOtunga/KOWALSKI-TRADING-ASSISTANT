from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    secret_str: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

#secret_str is loaded from .env file and not manually filled in here.
settings = Settings() # pyright: ignore[reportCallIssue]
