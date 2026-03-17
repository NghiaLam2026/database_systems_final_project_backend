"""Application settings loaded from environment."""
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """App config. All fields can be overridden via env vars or .env file."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "PC Build Assistant API"
    debug: bool = False

    # Database (same DATABASE_URL as Alembic when .env is at project root)
    database_url: str = Field(
        default="postgresql+psycopg2://localhost:5432/pcbuild",
        alias="DATABASE_URL",
    )

    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS (comma-separated origins, or "*")
    cors_origins: str = "http://localhost:3000"

@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()