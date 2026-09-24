from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ProviderMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class ProviderResult:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None


@dataclass(frozen=True)
class ProviderChunk:
    delta: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None


class ProviderError(Exception):
    pass


class ProviderConfigurationError(ProviderError):
    pass


class ProviderClient(Protocol):
    name: str
    model: str

    async def complete(
        self,
        messages: list[ProviderMessage],
        max_output_tokens: int,
    ) -> ProviderResult:
        ...

    def stream(
        self,
        messages: list[ProviderMessage],
        max_output_tokens: int,
    ) -> AsyncIterator[ProviderChunk]:
        ...
