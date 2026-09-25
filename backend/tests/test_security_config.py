import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_requires_persistent_high_entropy_pepper() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", cookie_secure=True)
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            cookie_secure=True,
            auth_pepper="short",
        )


def test_production_requires_secure_cookies() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            auth_pepper="a" * 32,
            cookie_secure=False,
        )


def test_cookie_names_must_be_safe() -> None:
    with pytest.raises(ValidationError):
        Settings(session_cookie_name="roleverse session")


def test_secure_production_settings_are_accepted() -> None:
    settings = Settings(
        environment="production",
        auth_pepper="a" * 32,
        cookie_secure=True,
    )
    assert settings.environment == "production"
    assert settings.cookie_secure is True


def test_cors_origins_are_explicit_origins() -> None:
    with pytest.raises(ValueError):
        Settings(cors_origins="https://example.com/path").cors_origin_list
    with pytest.raises(ValueError):
        Settings(cors_origins="null").cors_origin_list
    assert Settings(cors_origins="HTTPS://EXAMPLE.COM/").cors_origin_list == ["https://example.com"]


def test_environment_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="prod")
