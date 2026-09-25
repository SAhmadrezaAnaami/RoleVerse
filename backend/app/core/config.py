import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
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
    environment: Literal["development", "test", "staging", "production"] = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./roleverse.db"
    god_user_phone: str = ""
    auth_pepper: str = Field(default="", repr=False)
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
    provider_fixture_path: Path | None = None
    provider_allowed_hosts: str = ""
    live_provider_enabled: bool = False
    provider_timeout_seconds: int = Field(default=60, ge=1, le=300)
    provider_max_output_tokens: int = Field(default=512, ge=1, le=8192)
    provider_max_output_characters: int = Field(default=200000, ge=1024, le=2000000)
    provider_input_price_micro_per_million: int = Field(default=0, ge=0)
    provider_output_price_micro_per_million: int = Field(default=0, ge=0)
    generation_rate_limit_per_user: int = Field(default=20, ge=1, le=1000)
    generation_rate_limit_global: int = Field(default=100, ge=1, le=10000)
    generation_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    client_directory: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "client"
    )
    cors_origins: str = "http://localhost:8000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        normalized: list[str] = []
        for origin in origins:
            if origin == "null" or "*" in origin:
                raise ValueError("CORS_ORIGINS must use explicit origins.")
            try:
                parsed = urlparse(origin)
                port = parsed.port
            except ValueError as error:
                raise ValueError("CORS_ORIGINS contains a malformed origin.") from error
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.path not in {"", "/"}
            ):
                raise ValueError("CORS_ORIGINS must contain origins only.")
            host = parsed.hostname.lower().rstrip(".")
            port_suffix = f":{port}" if port else ""
            normalized.append(f"{parsed.scheme.lower()}://{host}{port_suffix}")
        return normalized

    @field_validator("auth_pepper", mode="before")
    @classmethod
    def normalize_auth_pepper(cls, value):
        if value is None:
            return ""
        return str(value).strip()

    @model_validator(mode="after")
    def validate_security_settings(self):
        secure_environment = self.environment in {"staging", "production"}
        if not self.auth_pepper:
            if secure_environment:
                raise ValueError("AUTH_PEPPER is required for staging and production.")
            self.auth_pepper = secrets.token_urlsafe(32)
        if secure_environment and len(self.auth_pepper) < 32:
            raise ValueError("AUTH_PEPPER must be at least 32 characters for staging and production.")
        if secure_environment and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true for staging and production.")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SAMESITE=None requires COOKIE_SECURE=true.")
        for cookie_name in (self.session_cookie_name,):
            if not cookie_name or any(character in cookie_name for character in (" ", ";", "\r", "\n")):
                raise ValueError("Cookie names must be non-empty and contain no separators.")
        return self

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
