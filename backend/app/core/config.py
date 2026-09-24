import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.phone import normalize_phone


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    app_name: str = "RoleVerse"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./roleverse.db"
    god_user_phone: str = ""
    auth_pepper: str = Field(default_factory=lambda: secrets.token_urlsafe(32), repr=False)
    session_cookie_name: str = "roleverse_session"
    session_ttl_minutes: int = 1440
    otp_ttl_minutes: int = 5
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    openai_api_key: SecretStr | None = None
    openai_base_url: str = ""
    openai_model: str = ""
    client_directory: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "client"
    )
    cors_origins: str = "http://localhost:8000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if "*" in origins or "null" in origins:
            raise ValueError("CORS_ORIGINS must use explicit origins.")
        return origins

    @field_validator("auth_pepper", mode="before")
    @classmethod
    def create_auth_pepper(cls, value):
        if isinstance(value, str) and not value.strip():
            return secrets.token_urlsafe(32)
        return value

    @field_validator("god_user_phone")
    @classmethod
    def validate_god_user_phone(cls, value: str) -> str:
        if not value.strip():
            return ""
        try:
            return normalize_phone(value)
        except ValueError as error:
            raise ValueError("GOD_USER_PHONE must be a valid phone number.") from error


@lru_cache
def get_settings() -> Settings:
    return Settings()
