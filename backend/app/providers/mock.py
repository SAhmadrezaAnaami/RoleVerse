from collections.abc import AsyncIterator

from app.providers.base import ProviderChunk, ProviderMessage, ProviderResult


class MockProvider:
    name = "mock"
    model = "roleverse-preview"

    async def complete(
        self,
        messages: list[ProviderMessage],
        max_output_tokens: int,
    ) -> ProviderResult:
        content_parts = []
        input_tokens = 0
        output_tokens = 0
        async for chunk in self.stream(messages, max_output_tokens):
            content_parts.append(chunk.delta)
            if chunk.input_tokens is not None:
                input_tokens = chunk.input_tokens
            if chunk.output_tokens is not None:
                output_tokens = chunk.output_tokens
        return ProviderResult(
            content="".join(content_parts),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[ProviderMessage],
        max_output_tokens: int,
    ) -> AsyncIterator[ProviderChunk]:
        latest_user_message = next(
            (message.content for message in reversed(messages) if message.role == "user"),
            "the story",
        )
        response = (
            "I heard you. "
            f"Let’s explore this together: {latest_user_message[:180]} "
            "What detail should we uncover next?"
        )
        words = response.split()[:max_output_tokens]
        for index in range(0, len(words), 5):
            delta = " ".join(words[index:index + 5])
            if index:
                delta = f" {delta}"
            yield ProviderChunk(delta=delta)
        input_tokens = max(1, sum(len(message.content) for message in messages) // 4)
        output_tokens = max(1, len(words))
        yield ProviderChunk(
            delta="",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason="stop",
        )
