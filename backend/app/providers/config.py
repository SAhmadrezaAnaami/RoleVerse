import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import Settings
from app.providers.base import ProviderConfigurationError
from app.providers.openai_compatible import OpenAIProviderConfig


def validate_provider_url(
    value: str,
    environment: str,
    allowed_hosts: set[str] | None = None,
) -> None:
    if any(ord(character) < 32 for character in value):
        raise ProviderConfigurationError("Provider URL contains an invalid character.")
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError as error:
        raise ProviderConfigurationError("Provider URL is malformed.") from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ProviderConfigurationError("Provider URL must be an HTTP or HTTPS URL.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProviderConfigurationError("Provider URL cannot contain credentials, query parameters, or fragments.")
    production = environment.lower() == "production"
    if production and parsed.scheme != "https":
        raise ProviderConfigurationError("Production provider URLs must use HTTPS.")
    if production and port not in {None, 80, 443}:
        raise ProviderConfigurationError("Production provider URLs must use a standard port.")
    hostname = parsed.hostname.lower().rstrip(".")
    if production and (hostname == "localhost" or hostname.endswith(".local")):
        raise ProviderConfigurationError("Provider URL cannot target a local hostname.")
    if production and not allowed_hosts:
        raise ProviderConfigurationError("Production provider hosts require an explicit allowlist.")
    if production and allowed_hosts is not None and hostname not in allowed_hosts:
        raise ProviderConfigurationError("Provider URL is not in the configured host allowlist.")
    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as error:
        if production:
            raise ProviderConfigurationError("Provider URL host could not be resolved.") from error
        addresses = set()
    for address in addresses:
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            if production:
                raise ProviderConfigurationError("Provider URL cannot target a private or reserved address.")


def load_provider_config(settings: Settings) -> OpenAIProviderConfig:
    if not settings.live_provider_enabled:
        raise ProviderConfigurationError("Live provider access is disabled.")
    fixture_path = settings.provider_fixture_path
    if fixture_path is not None:
        if settings.environment.lower() == "production":
            raise ProviderConfigurationError("Provider fixtures are not allowed in production.")
        path = Path(fixture_path)
        if not path.is_file():
            raise ProviderConfigurationError("Provider fixture was not found.")
        try:
            fixture = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProviderConfigurationError("Provider fixture could not be loaded.") from error
        base_url = str(fixture.get("base_url", ""))
        api_key = str(fixture.get("api_key", ""))
        model = str(fixture.get("model", ""))
    else:
        base_url = settings.openai_base_url
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
        model = settings.openai_model
    if not base_url or not api_key or not model:
        raise ProviderConfigurationError("Live provider requires a base URL, API key, and model.")
    allowed_hosts = {
        host.strip().lower().rstrip(".")
        for host in settings.provider_allowed_hosts.split(",")
        if host.strip()
    }
    if settings.environment.lower() == "production" and not allowed_hosts:
        raise ProviderConfigurationError("Production provider hosts require an explicit allowlist.")
    validate_provider_url(
        base_url,
        settings.environment,
        allowed_hosts or None,
    )
    return OpenAIProviderConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=settings.provider_timeout_seconds,
        max_output_characters=settings.provider_max_output_characters,
    )
