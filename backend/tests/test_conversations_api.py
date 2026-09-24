from fastapi.testclient import TestClient

from app.db.models import Conversation, User


def login(client, otp_sender, phone: str) -> dict:
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
    return verify_response.json()


def create_conversation(client, locale: str = "en") -> dict:
    response = client.post(
        "/api/v1/conversations",
        json={"character_slug": "luna-vale", "locale": locale},
    )
    assert response.status_code == 201
    return response.json()


def test_conversation_creation_persists_localized_greeting(api_client, otp_sender) -> None:
    login(api_client, otp_sender, "+15551234567")
    conversation = create_conversation(api_client, "fa")
    assert conversation["locale"] == "fa"
    assert conversation["character"]["name"] == "لونا ویل"

    messages_response = api_client.get(
        f"/api/v1/conversations/{conversation['id']}/messages",
    )
    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["position"] == 1
    assert "آسمان" in messages[0]["content"]


def test_message_send_is_ordered_and_idempotent(api_client, otp_sender) -> None:
    login(api_client, otp_sender, "+15551234567")
    conversation = create_conversation(api_client)
    path = f"/api/v1/conversations/{conversation['id']}/messages"
    payload = {
        "content": "Should we make a wish?",
        "client_request_id": "request-001",
    }

    first_response = api_client.post(path, json=payload)
    assert first_response.status_code == 201
    first_body = first_response.json()
    assert first_body["mode"] == "preview"
    assert first_body["user_message"]["position"] == 2
    assert first_body["assistant_message"]["position"] == 3

    retry_response = api_client.post(path, json=payload)
    assert retry_response.status_code == 201
    retry_body = retry_response.json()
    assert retry_body["user_message"]["id"] == first_body["user_message"]["id"]
    assert retry_body["assistant_message"]["id"] == first_body["assistant_message"]["id"]

    conflict_response = api_client.post(
        path,
        json={**payload, "content": "Different content"},
    )
    assert conflict_response.status_code == 409

    messages = api_client.get(path).json()
    assert [message["position"] for message in messages] == [1, 2, 3]


def test_persist_message_retry_does_not_duplicate_user_turn(api_client, otp_sender) -> None:
    login(api_client, otp_sender, "+15551234567")
    conversation = create_conversation(api_client)
    path = f"/api/v1/conversations/{conversation['id']}/messages"
    payload = {
        "content": "A turn waiting for its response.",
        "client_request_id": "persist-request-001",
        "mode": "persist",
    }

    first = api_client.post(path, json=payload)
    retry = api_client.post(path, json=payload)

    assert first.status_code == 201
    assert first.json()["assistant_message"] is None
    assert retry.status_code == 201
    assert retry.json()["user_message"]["id"] == first.json()["user_message"]["id"]
    assert len(api_client.get(path).json()) == 2


def test_conversation_routes_require_authentication(application) -> None:
    with TestClient(application, base_url="https://testserver") as client:
        assert client.get("/api/v1/conversations").status_code == 401
        assert client.post(
            "/api/v1/conversations",
            json={"character_slug": "luna-vale"},
        ).status_code == 401


def test_user_cannot_read_another_users_conversation(
    api_client,
    otp_sender,
    migrated_db,
) -> None:
    login(api_client, otp_sender, "+15551234567")
    conversation = create_conversation(api_client)
    session_factory, _ = migrated_db
    with session_factory() as session:
        other_user = User(phone="+15557654321", role="user")
        session.add(other_user)
        session.flush()
        session.add(
            Conversation(
                user_id=other_user.id,
                character_id=conversation["character"]["id"],
                title="Private conversation",
                locale="en",
            )
        )
        session.commit()
        other_conversation_id = session.query(Conversation).filter_by(title="Private conversation").one().id

    assert api_client.get(
        f"/api/v1/conversations/{other_conversation_id}",
    ).status_code == 404
