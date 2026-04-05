"""Application settings loaded from environment."""
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """App config. All fields can be overridden via env vars or .env file."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
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
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # CORS (comma-separated origins, or "*")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # Bootstrap admin (source-of-truth admin is configured via .env)
    # If ADMIN_EMAIL is set, app ensures an admin user exists on startup.
    admin_email: str | None = Field(default=None, alias="ADMIN_EMAIL")
    admin_password: str | None = Field(default=None, alias="ADMIN_PASSWORD")
    admin_first_name: str = Field(default="Admin", alias="ADMIN_FIRST_NAME")
    admin_last_name: str = Field(default="User", alias="ADMIN_LAST_NAME")

    # Google Gemini (chat orchestrator)
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        alias="GEMINI_MODEL",
        description="Gemini model id for google-genai client.models.generate_content.",
    )

@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()