from app.core.config import Settings
from app.providers.base import ProviderClient
from app.providers.config import load_provider_config
from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


def get_provider(settings: Settings) -> ProviderClient:
    if not settings.live_provider_enabled:
        return MockProvider()
    return OpenAICompatibleProvider(load_provider_config(settings))
