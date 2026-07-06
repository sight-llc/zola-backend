from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Postgres
    database_url: str = "postgresql+asyncpg://zola:zola@localhost:5432/zola"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # Meroe (NombaVault) — the BaaS infrastructure
    meroe_base_url: str = "http://localhost:8080"
    meroe_api_key: str = ""  # set via env: MEROE_API_KEY

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
