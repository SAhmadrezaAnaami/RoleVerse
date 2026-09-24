import asyncio
import json

import httpx
from openai import AsyncOpenAI

from app.providers.base import ProviderMessage
from app.providers.openai_compatible import OpenAICompatibleProvider, OpenAIProviderConfig


def test_openai_compatible_adapter_normalizes_json_and_stream() -> None:
    async def exercise() -> tuple:
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            request_body = json.loads(request.content)
            if request.url.path.endswith("/chat/completions") and request_body.get("stream") is True:
                return httpx.Response(
                    200,
                    headers={"content-type": "text/event-stream"},
                    content=(
                        'data: {"id":"chunk-1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Hel"},"finish_reason":null}]}\n\n'
                        'data: {"id":"chunk-2","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"lo"},"finish_reason":"stop"}]}\n\n'
                        'data: {"id":"chunk-3","object":"chat.completion.chunk","choices":[],"usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5}}\n\n'
                        "data: [DONE]\n\n"
                    ),
                )
            return httpx.Response(
                200,
                json={
                    "id": "completion-1",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "Complete"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 4, "completion_tokens": 1, "total_tokens": 5},
                },
            )

        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AsyncOpenAI(
            api_key="test-key",
            base_url="https://provider.example/v1",
            http_client=http_client,
        )
        provider = OpenAICompatibleProvider(
            OpenAIProviderConfig(
                base_url="https://provider.example/v1",
                api_key="test-key",
                model="test-model",
            ),
            client=client,
        )
        result = await provider.complete(
            [ProviderMessage(role="user", content="Hello")],
            32,
        )
        chunks = [
            chunk
            async for chunk in provider.stream(
                [ProviderMessage(role="user", content="Hello")],
                32,
            )
        ]
        await http_client.aclose()
        return result, chunks, requests

    result, chunks, requests = asyncio.run(exercise())
    assert result.content == "Complete"
    assert result.input_tokens == 4
    assert result.output_tokens == 1
    assert "".join(chunk.delta for chunk in chunks) == "Hello"
    assert any(chunk.input_tokens == 3 and chunk.output_tokens == 2 for chunk in chunks)
    assert all(request.headers["authorization"] == "Bearer test-key" for request in requests)
