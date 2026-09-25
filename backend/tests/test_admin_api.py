from fastapi.testclient import TestClient

from app.api.routes.admin import redacted_provider_endpoint
from app.core.phone import mask_phone
from app.db.models import SystemSetting


def login(client, otp_sender, phone: str) -> None:
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


def csrf_headers(client) -> dict[str, str]:
    return {
        "Origin": "https://testserver",
        "X-CSRF-Token": client.cookies.get("roleverse_csrf") or "",
    }


def test_provider_endpoint_response_is_redacted() -> None:
    value = redacted_provider_endpoint("https://internal.example:8443/v1/private/path")
    assert value == "https://internal.example:8443"
    assert "/private/path" not in value


def test_cors_preflight_allows_csrf_header(api_client) -> None:
    response = api_client.options(
        "/api/v1/admin/overview",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "X-CSRF-Token",
        },
    )
    assert response.status_code == 200
    assert "X-CSRF-Token" in response.headers["access-control-allow-headers"]


def test_admin_static_surface_sets_security_headers(application) -> None:
    with TestClient(application, base_url="https://testserver") as client:
        response = client.get("/admin/")
        root_response = client.get("/")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "script-src 'self'" in root_response.headers["content-security-policy"]
    assert "cdn.tailwindcss.com" not in root_response.text


def test_admin_routes_require_admin_role(api_client, otp_sender) -> None:
    anonymous = api_client.get("/api/v1/admin/overview")
    assert anonymous.status_code == 401

    login(api_client, otp_sender, "+15551234567")
    forbidden = api_client.get("/api/v1/admin/overview")
    assert forbidden.status_code == 403


def test_admin_overview_masks_phone_numbers_and_lists_seeded_provider(
    api_client,
    otp_sender,
) -> None:
    login(api_client, otp_sender, "+15550000000")
    overview = api_client.get("/api/v1/admin/overview")
    assert overview.status_code == 200
    assert overview.headers["cache-control"] == "no-store"
    assert overview.json()["metrics"]["providers_total"] == 1
    assert overview.json()["provider_runtime_mode"] == "mock"
    assert overview.json()["rate_limit_policy"]["max_output_tokens"] == 512

    users = api_client.get("/api/v1/admin/users")
    assert users.status_code == 200
    god_user = users.json()["items"][0]
    identity = api_client.get("/api/v1/admin/me")
    assert identity.status_code == 200
    assert identity.json()["phone_masked"] == mask_phone("+15550000000")
    assert identity.json()["is_god_user"] is True
    assert "phone" not in identity.json()
    assert god_user["phone_masked"] == mask_phone("+15550000000")
    assert "phone" not in god_user


def test_admin_ban_is_audited_and_protects_admin_accounts(
    application,
    api_client,
    otp_sender,
) -> None:
    login(api_client, otp_sender, "+15551234567")
    target_session = api_client.cookies.get("roleverse_session")
    login(api_client, otp_sender, "+15550000000")
    users = api_client.get("/api/v1/admin/users?search=15551234567").json()
    target = users["items"][0]
    admin = api_client.get("/api/v1/admin/users?search=15550000000").json()["items"][0]

    response = api_client.post(
        f"/api/v1/admin/users/{target['id']}/ban",
        headers=csrf_headers(api_client),
        json={"reason": "Development moderation test"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "banned"
    assert response.headers["cache-control"] == "no-store"
    with TestClient(application, base_url="https://testserver") as target_client:
        target_client.cookies.set("roleverse_session", target_session)
        assert target_client.get("/api/v1/auth/me").status_code == 401
    api_client.cookies.clear()
    login(api_client, otp_sender, "+15550000000")

    audit = api_client.get("/api/v1/admin/audit").json()
    assert any(event["action"] == "user.banned" for event in audit)

    self_ban = api_client.post(
        f"/api/v1/admin/users/{admin['id']}/ban",
        headers=csrf_headers(api_client),
        json={"reason": "Self-ban attempt"},
    )
    assert self_ban.status_code == 422

    demote = api_client.patch(
        f"/api/v1/admin/users/{admin['id']}/role",
        headers=csrf_headers(api_client),
        json={"role": "user"},
    )
    assert demote.status_code == 422


def test_admin_mutations_require_same_origin(api_client, otp_sender) -> None:
    login(api_client, otp_sender, "+15550000000")
    api_client.auto_security_headers = False
    response = api_client.patch(
        "/api/v1/admin/settings/maintenance_mode",
        json={"value": True},
    )
    assert response.status_code == 403


def test_admin_mutations_require_csrf_token(api_client, otp_sender) -> None:
    login(api_client, otp_sender, "+15550000000")
    api_client.auto_security_headers = False
    missing = api_client.patch(
        "/api/v1/admin/settings/maintenance_mode",
        headers={"Origin": "https://testserver"},
        json={"value": True},
    )
    assert missing.status_code == 403
    api_client.auto_security_headers = True
    invalid = api_client.patch(
        "/api/v1/admin/settings/maintenance_mode",
        headers={"Origin": "https://testserver", "X-CSRF-Token": "invalid"},
        json={"value": True},
    )
    assert invalid.status_code == 403
    valid = api_client.patch(
        "/api/v1/admin/settings/maintenance_mode",
        headers=csrf_headers(api_client),
        json={"value": True},
    )
    assert valid.status_code == 200

    old_token = api_client.cookies.get("roleverse_csrf")
    api_client.post("/api/v1/auth/logout")
    login(api_client, otp_sender, "+15550000000")
    rotated = api_client.patch(
        "/api/v1/admin/settings/maintenance_mode",
        headers={"Origin": "https://testserver", "X-CSRF-Token": old_token or ""},
        json={"value": False},
    )
    assert rotated.status_code == 403


def test_only_god_user_can_change_roles(
    application,
    api_client,
    otp_sender,
) -> None:
    login(api_client, otp_sender, "+15551234567")
    target_session = api_client.cookies.get("roleverse_session")
    api_client.post("/api/v1/auth/logout")
    login(api_client, otp_sender, "+15550000000")
    target = api_client.get("/api/v1/admin/users?search=15551234567").json()["items"][0]
    promoted = api_client.patch(
        f"/api/v1/admin/users/{target['id']}/role",
        headers=csrf_headers(api_client),
        json={"role": "admin"},
    )
    assert promoted.status_code == 200
    with TestClient(application, base_url="https://testserver") as old_target_client:
        old_target_client.cookies.set("roleverse_session", target_session)
        assert old_target_client.get("/api/v1/auth/me").status_code == 401
    api_client.post("/api/v1/auth/logout")
    login(api_client, otp_sender, "+15551234567")
    forbidden = api_client.patch(
        f"/api/v1/admin/users/{target['id']}/role",
        headers=csrf_headers(api_client),
        json={"role": "user"},
    )
    assert forbidden.status_code == 403


def test_admin_can_revoke_user_sessions_atomically(
    application,
    api_client,
    otp_sender,
) -> None:
    login(api_client, otp_sender, "+15551234567")
    target_session = api_client.cookies.get("roleverse_session")
    login(api_client, otp_sender, "+15550000000")
    target = api_client.get("/api/v1/admin/users?search=15551234567").json()["items"][0]
    response = api_client.post(
        f"/api/v1/admin/users/{target['id']}/revoke-sessions",
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 200
    with TestClient(application, base_url="https://testserver") as old_client:
        old_client.cookies.set("roleverse_session", target_session)
        assert old_client.get("/api/v1/auth/me").status_code == 401
    audit = api_client.get("/api/v1/admin/audit").json()
    assert any(event["action"] == "user.sessions_revoked" for event in audit)


def test_admin_can_manage_provider_metadata_without_secrets(
    api_client,
    otp_sender,
) -> None:
    login(api_client, otp_sender, "+15550000000")
    provider_response = api_client.post(
        "/api/v1/admin/providers",
        headers=csrf_headers(api_client),
        json={
            "name": "Test Provider",
            "slug": "test-provider",
            "adapter": "mock",
            "status": "enabled",
            "is_default": False,
            "secret_source": "none",
        },
    )
    assert provider_response.status_code == 201
    provider = provider_response.json()
    assert "api_key" not in provider
    assert provider["secret_source"] == "none"
    assert provider["runtime_mode"] == "mock"
    assert provider["activation_supported"] is False
    rejected_secret = api_client.post(
        "/api/v1/admin/providers",
        headers=csrf_headers(api_client),
        json={
            "name": "Unsafe Provider",
            "slug": "unsafe-provider",
            "adapter": "mock",
            "api_key": "should-not-be-accepted",
        },
    )
    assert rejected_secret.status_code == 422

    model_response = api_client.post(
        f"/api/v1/admin/providers/{provider['id']}/models",
        headers=csrf_headers(api_client),
        json={
            "name": "test-model",
            "display_name": "Test Model",
            "context_window": 8000,
            "max_output_tokens": 256,
        },
    )
    assert model_response.status_code == 201
    assert model_response.json()["name"] == "test-model"


def test_admin_settings_hide_unrecognized_values(
    api_client,
    otp_sender,
    migrated_db,
) -> None:
    session_factory, _ = migrated_db
    with session_factory() as session:
        session.add(SystemSetting(key="auth_pepper", value="must-not-be-returned"))
        session.commit()
    login(api_client, otp_sender, "+15550000000")
    settings = api_client.get("/api/v1/admin/settings")
    assert settings.status_code == 200
    assert all(setting["key"] != "auth_pepper" for setting in settings.json())
    assert "must-not-be-returned" not in settings.text


def test_admin_settings_validate_ranges_and_write_audit(api_client, otp_sender) -> None:
    login(api_client, otp_sender, "+15550000000")
    invalid = api_client.patch(
        "/api/v1/admin/settings/generation_rate_limit_per_user",
        headers=csrf_headers(api_client),
        json={"value": 0},
    )
    assert invalid.status_code == 422

    rate_policy = api_client.get("/api/v1/admin/rate-limits")
    assert rate_policy.status_code == 200
    updated_policy = api_client.put(
        "/api/v1/admin/rate-limits",
        headers=csrf_headers(api_client),
        json={
            "per_user_limit": 30,
            "global_limit": 120,
            "window_seconds": 60,
            "max_output_tokens": 256,
        },
    )
    assert updated_policy.status_code == 200
    assert updated_policy.json()["per_user_limit"] == 30

    valid = api_client.patch(
        "/api/v1/admin/settings/generation_rate_limit_per_user",
        headers=csrf_headers(api_client),
        json={"value": 25},
    )
    assert valid.status_code == 200
    assert valid.json()["value"] == 25
    audit = api_client.get("/api/v1/admin/audit").json()
    assert any(event["action"] == "setting.updated" for event in audit)
