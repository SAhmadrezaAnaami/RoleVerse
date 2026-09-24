from collections.abc import AsyncIterator

from app.api.deps import get_provider_client
from app.db.models import GenerationRun, Message
from app.providers.base import ProviderChunk, ProviderError, ProviderMessage, ProviderResult


class RecordingProvider:
    name = "recording"
    model = "test-model"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(
        self,
        messages: list[ProviderMessage],
        max_output_tokens: int,
    ) -> ProviderResult:
        self.calls += 1
        return ProviderResult(content="complete", input_tokens=1, output_tokens=1)

    async def stream(
        self,
        messages: list[ProviderMessage],
        max_output_tokens: int,
    ) -> AsyncIterator[ProviderChunk]:
        self.calls += 1
        yield ProviderChunk(delta="Hello")
        yield ProviderChunk(delta=" from the stream")
        yield ProviderChunk(
            delta="",
            input_tokens=11,
            output_tokens=7,
            finish_reason="stop",
        )


class FailingProvider(RecordingProvider):
    async def stream(
        self,
        messages: list[ProviderMessage],
        max_output_tokens: int,
    ) -> AsyncIterator[ProviderChunk]:
        self.calls += 1
        if False:
            yield ProviderChunk()
        raise ProviderError("secret upstream details")


def login(client, otp_sender, phone: str = "+15551234567") -> None:
    request_response = client.post(
        "/api/v1/auth/otp/request",
        json={"phone": phone},
    )
    assert request_response.status_code == 202
    code = otp_sender.sent[-1][1]
    verify_response = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "code": code},
    )
    assert verify_response.status_code == 200


def create_persisted_turn(client) -> dict:
    conversation_response = client.post(
        "/api/v1/conversations",
        json={"character_slug": "luna-vale", "locale": "en"},
    )
    assert conversation_response.status_code == 201
    conversation = conversation_response.json()
    message_response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={
            "content": "Tell me a small mystery.",
            "client_request_id": "generation-request-1",
            "mode": "persist",
        },
    )
    assert message_response.status_code == 201
    assert message_response.json()["assistant_message"] is None
    return {
        "conversation": conversation,
        "message": message_response.json()["user_message"],
    }


def test_streaming_generation_persists_run_and_message(
    application,
    api_client,
    otp_sender,
    migrated_db,
) -> None:
    provider = RecordingProvider()
    application.dependency_overrides[get_provider_client] = lambda: provider
    login(api_client, otp_sender)
    turn = create_persisted_turn(api_client)

    response = api_client.post(
        f"/api/v1/conversations/{turn['conversation']['id']}/messages/{turn['message']['id']}/responses",
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "no-store" in response.headers["cache-control"]
    assert response.headers["x-accel-buffering"] == "no"
    assert "event: start" in response.text
    assert "event: delta" in response.text
    assert "event: done" in response.text
    assert "Hello from the stream" in response.text
    assert provider.calls == 1

    messages_response = api_client.get(
        f"/api/v1/conversations/{turn['conversation']['id']}/messages",
    )
    messages = messages_response.json()
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == "Hello from the stream"

    session_factory, _ = migrated_db
    with session_factory() as session:
        run = session.query(GenerationRun).one()
        assistant = session.query(Message).filter_by(source="generation").one()
        assert run.status == "complete"
        assert run.usage_available is True
        assert run.input_tokens == 11
        assert run.output_tokens == 7
        assert assistant.status == "complete"
        run_id = run.id

    status_response = api_client.get(
        f"/api/v1/conversations/{turn['conversation']['id']}/generations/{run_id}",
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "complete"
    cancel_response = api_client.post(
        f"/api/v1/conversations/{turn['conversation']['id']}/generations/{run_id}/cancel",
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "complete"

    replay = api_client.post(
        f"/api/v1/conversations/{turn['conversation']['id']}/messages/{turn['message']['id']}/responses",
    )
    assert replay.status_code == 200
    assert "event: done" in replay.text
    assert provider.calls == 1


def test_non_streaming_generation_returns_message_pair(
    application,
    api_client,
    otp_sender,
    migrated_db,
) -> None:
    provider = RecordingProvider()
    application.dependency_overrides[get_provider_client] = lambda: provider
    login(api_client, otp_sender)
    turn = create_persisted_turn(api_client)

    response = api_client.post(
        f"/api/v1/conversations/{turn['conversation']['id']}/messages/{turn['message']['id']}/response",
    )
    assert response.status_code == 200
    assert response.json()["assistant_message"]["content"] == "complete"
    assert provider.calls == 1

    session_factory, _ = migrated_db
    with session_factory() as session:
        run = session.query(GenerationRun).one()
        assert run.status == "complete"
        assert run.input_tokens == 1
        assert run.output_tokens == 1


def test_streaming_generation_failure_is_safe_and_persisted(
    application,
    api_client,
    otp_sender,
    migrated_db,
) -> None:
    provider = FailingProvider()
    application.dependency_overrides[get_provider_client] = lambda: provider
    login(api_client, otp_sender)
    turn = create_persisted_turn(api_client)

    response = api_client.post(
        f"/api/v1/conversations/{turn['conversation']['id']}/messages/{turn['message']['id']}/responses",
    )
    assert response.status_code == 200
    assert "event: error" in response.text
    assert "secret upstream details" not in response.text
    assert "provider_unavailable" in response.text

    session_factory, _ = migrated_db
    with session_factory() as session:
        run = session.query(GenerationRun).one()
        assistant = session.query(Message).filter_by(source="generation").one()
        assert run.status == "failed"
        assert run.error_code == "provider_unavailable"
        assert assistant.status == "failed"
