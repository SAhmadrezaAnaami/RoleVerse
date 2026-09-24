from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from inspect import isawaitable

from openai import AsyncOpenAI

from app.providers.base import ProviderChunk, ProviderError, ProviderMessage, ProviderResult


@dataclass(frozen=True)
class OpenAIProviderConfig:
    base_url: str
    api_key: str = field(repr=False)
    model: str
    timeout_seconds: int = 60


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self, config: OpenAIProviderConfig, client=None) -> None:
        self.config = config
        self.model = config.model
        self.client = client or AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )

    async def complete(
        self,
        messages: list[ProviderMessage],
        max_output_tokens: int,
    ) -> ProviderResult:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": message.role, "content": message.content} for message in messages],
                max_tokens=max_output_tokens,
                stream=False,
            )
            choice = response.choices[0] if response.choices else None
            content = getattr(getattr(choice, "message", None), "content", "") or ""
            usage = getattr(response, "usage", None)
            return ProviderResult(
                content=content,
                input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
                output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
                finish_reason=getattr(choice, "finish_reason", None) if choice else None,
            )
        except Exception as error:
            raise ProviderError("Provider request failed.") from error

    async def stream(
        self,
        messages: list[ProviderMessage],
        max_output_tokens: int,
    ) -> AsyncIterator[ProviderChunk]:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": message.role, "content": message.content} for message in messages],
                max_tokens=max_output_tokens,
                stream=True,
            )
            input_tokens = 0
            output_tokens = 0
            async for event in response:
                usage = getattr(event, "usage", None)
                if usage is not None:
                    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
                    output_tokens = getattr(usage, "completion_tokens", 0) or 0
                choices = getattr(event, "choices", None) or []
                if not choices:
                    continue
                choice = choices[0]
                delta = getattr(getattr(choice, "delta", None), "content", None)
                if delta:
                    yield ProviderChunk(delta=delta)
                finish_reason = getattr(choice, "finish_reason", None)
                if finish_reason:
                    yield ProviderChunk(
                        delta="",
                        input_tokens=input_tokens or None,
                        output_tokens=output_tokens or None,
                        finish_reason=finish_reason,
                    )
            if input_tokens or output_tokens:
                yield ProviderChunk(
                    delta="",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    finish_reason="stop",
                )
        except ProviderError:
            raise
        except Exception as error:
            raise ProviderError("Provider request failed.") from error
