import json

import pytest

from app.core.config import Settings
from app.providers import ProviderConfigurationError, get_provider, load_provider_config, validate_provider_url
from app.providers.mock import MockProvider


def test_default_provider_is_mock_even_when_credentials_exist() -> None:
    settings = Settings(
        live_provider_enabled=False,
        openai_api_key="unused-key",
        openai_base_url="https://api.example.com/v1",
        openai_model="test-model",
    )
    assert isinstance(get_provider(settings), MockProvider)


def test_live_provider_requires_complete_configuration() -> None:
    settings = Settings(live_provider_enabled=True)
    with pytest.raises(ProviderConfigurationError):
        load_provider_config(settings)


def test_production_live_provider_requires_an_explicit_host_allowlist() -> None:
    settings = Settings(
        live_provider_enabled=True,
        environment="production",
        auth_pepper="a" * 32,
        cookie_secure=True,
        openai_api_key="test-key",
        openai_base_url="https://api.example.com/v1",
        openai_model="test-model",
    )
    with pytest.raises(ProviderConfigurationError):
        load_provider_config(settings)


def test_provider_url_validation_blocks_unsafe_production_targets() -> None:
    with pytest.raises(ProviderConfigurationError):
        validate_provider_url("http://api.example.com/v1", "production")
    with pytest.raises(ProviderConfigurationError):
        validate_provider_url("https://127.0.0.1/v1", "production")
    with pytest.raises(ProviderConfigurationError):
        validate_provider_url("https://user:password@api.example.com/v1", "production")
    with pytest.raises(ProviderConfigurationError):
        validate_provider_url("https://api.example.com/v1?token=secret", "production")
    with pytest.raises(ProviderConfigurationError):
        validate_provider_url("https://api.example.com/v1", "production", {"other.example"})


def test_explicit_fixture_path_is_loaded_only_when_requested(tmp_path) -> None:
    fixture = tmp_path / "provider.json"
    fixture.write_text(
        json.dumps(
            {
                "base_url": "https://api.example.com/v1",
                "api_key": "fixture-key",
                "model": "fixture-model",
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(
        live_provider_enabled=True,
        provider_fixture_path=fixture,
        environment="test",
    )
    config = load_provider_config(settings)
    assert config.base_url == "https://api.example.com/v1"
    assert config.model == "fixture-model"
    assert "fixture-key" not in repr(config)


def test_production_rejects_provider_fixtures(tmp_path) -> None:
    fixture = tmp_path / "provider.json"
    fixture.write_text("{}", encoding="utf-8")
    settings = Settings(
        live_provider_enabled=True,
        provider_fixture_path=fixture,
        environment="production",
        auth_pepper="a" * 32,
        cookie_secure=True,
    )
    with pytest.raises(ProviderConfigurationError):
        load_provider_config(settings)
