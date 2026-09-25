from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import AuthSession, OtpChallenge, User


def request_code(client, otp_sender, phone: str) -> str:
    response = client.post(
        "/api/v1/auth/otp/request",
        json={"phone": phone},
    )
    assert response.status_code == 202
    assert "code" not in response.json()
    return otp_sender.sent[-1][1]


def test_otp_request_does_not_return_or_store_plaintext_code(
    api_client,
    otp_sender,
    migrated_db,
) -> None:
    code = request_code(api_client, otp_sender, "+1 (555) 123-4567")
    session_factory, _ = migrated_db
    with session_factory() as session:
        challenge = session.scalar(select(OtpChallenge))
        assert challenge is not None
        assert challenge.code_hash != code
        assert len(challenge.code_hash) == 64
        assert session.scalar(select(User)) is None


def test_auth_mutations_require_a_trusted_origin(api_client) -> None:
    api_client.auto_security_headers = False
    missing = api_client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+15551234567"},
    )
    assert missing.status_code == 403
    foreign = api_client.post(
        "/api/v1/auth/otp/request",
        headers={"Origin": "https://evil.example"},
        json={"phone": "+15551234567"},
    )
    assert foreign.status_code == 403


def test_first_login_creates_user_session_and_me(api_client, otp_sender, migrated_db) -> None:
    code = request_code(api_client, otp_sender, "+1 555 123 4567")
    response = api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+1 (555) 123-4567", "code": code},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["phone"] == "+15551234567"
    assert body["user"]["role"] == "user"
    assert "token" not in body
    assert response.headers["cache-control"] == "no-store"
    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "roleverse_csrf=" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie
    session_token = api_client.cookies.get("roleverse_session")
    csrf_token = api_client.cookies.get("roleverse_csrf")
    assert session_token
    assert csrf_token

    me_response = api_client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["id"] == body["user"]["id"]

    session_factory, _ = migrated_db
    with session_factory() as session:
        user = session.scalar(select(User))
        auth_session = session.scalar(select(AuthSession))
        assert user is not None
        assert auth_session is not None
        assert auth_session.token_hash != session_token
        assert auth_session.csrf_token_hash != csrf_token


def test_wrong_code_does_not_create_a_session(api_client, otp_sender, migrated_db) -> None:
    request_code(api_client, otp_sender, "+15551234567")
    response = api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15551234567", "code": "000000"},
    )

    assert response.status_code == 400
    assert "roleverse_session" not in api_client.cookies
    session_factory, _ = migrated_db
    with session_factory() as session:
        assert session.scalar(select(User)) is None
        assert session.scalar(select(AuthSession)) is None


def test_replay_and_resend_only_allow_the_newest_code(api_client, otp_sender) -> None:
    first_code = request_code(api_client, otp_sender, "+15551234567")
    second_code = request_code(api_client, otp_sender, "+15551234567")

    replay_response = api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15551234567", "code": first_code},
    )
    assert replay_response.status_code == 400

    success_response = api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15551234567", "code": second_code},
    )
    assert success_response.status_code == 200


def test_god_phone_is_elevated_from_server_configuration(api_client, otp_sender) -> None:
    code = request_code(api_client, otp_sender, "+1 555 000 0000")
    response = api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15550000000", "code": code},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"


def test_logout_invalidates_the_session(api_client, otp_sender) -> None:
    code = request_code(api_client, otp_sender, "+15551234567")
    api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15551234567", "code": code},
    )
    old_token = api_client.cookies.get("roleverse_session")

    logout_response = api_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204
    assert api_client.cookies.get("roleverse_session") is None

    api_client.cookies.set("roleverse_session", old_token)
    me_response = api_client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


def test_attempt_limit_invalidates_the_challenge(api_client, otp_sender) -> None:
    code = request_code(api_client, otp_sender, "+15551234567")
    for _ in range(3):
        response = api_client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+15551234567", "code": "999999"},
        )
        assert response.status_code == 400

    final_response = api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15551234567", "code": code},
    )
    assert final_response.status_code == 400
    assert "roleverse_session" not in api_client.cookies


def test_logout_all_invalidates_the_current_session(api_client, otp_sender) -> None:
    code = request_code(api_client, otp_sender, "+15551234567")
    api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15551234567", "code": code},
    )
    old_token = api_client.cookies.get("roleverse_session")

    response = api_client.post("/api/v1/auth/logout-all")
    assert response.status_code == 204
    api_client.cookies.set("roleverse_session", old_token)
    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_logout_all_invalidates_all_sessions_but_not_other_users(
    application,
    api_client,
    otp_sender,
) -> None:
    first_code = request_code(api_client, otp_sender, "+15551234567")
    api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15551234567", "code": first_code},
    )
    first_token = api_client.cookies.get("roleverse_session")
    api_client.post("/api/v1/auth/logout")
    second_code = request_code(api_client, otp_sender, "+15551234567")
    api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15551234567", "code": second_code},
    )
    second_token = api_client.cookies.get("roleverse_session")
    assert first_token != second_token
    assert api_client.post("/api/v1/auth/logout-all").status_code == 204
    for old_token in (first_token, second_token):
        with TestClient(application, base_url="https://testserver") as old_client:
            old_client.cookies.set("roleverse_session", old_token)
            assert old_client.get("/api/v1/auth/me").status_code == 401

    other_code = request_code(api_client, otp_sender, "+15557654321")
    api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15557654321", "code": other_code},
    )
    other_token = api_client.cookies.get("roleverse_session")
    with TestClient(application, base_url="https://testserver") as other_client:
        other_client.cookies.set("roleverse_session", other_token)
        assert other_client.get("/api/v1/auth/me").status_code == 200


def test_expired_code_is_rejected(api_client, otp_sender, manual_clock) -> None:
    code = request_code(api_client, otp_sender, "+15551234567")
    manual_clock.advance(minutes=6)
    response = api_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+15551234567", "code": code},
    )

    assert response.status_code == 400
    assert "roleverse_session" not in api_client.cookies
