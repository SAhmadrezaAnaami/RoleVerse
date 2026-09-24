from fastapi.testclient import TestClient

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


def test_admin_static_surface_sets_security_headers(application) -> None:
    with TestClient(application, base_url="https://testserver") as client:
        response = client.get("/admin/")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "no-referrer"


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
        headers={"Origin": "https://testserver"},
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
        headers={"Origin": "https://testserver"},
        json={"reason": "Self-ban attempt"},
    )
    assert self_ban.status_code == 422

    demote = api_client.patch(
        f"/api/v1/admin/users/{admin['id']}/role",
        headers={"Origin": "https://testserver"},
        json={"role": "user"},
    )
    assert demote.status_code == 422


def test_admin_mutations_require_same_origin(api_client, otp_sender) -> None:
    login(api_client, otp_sender, "+15550000000")
    response = api_client.patch(
        "/api/v1/admin/settings/maintenance_mode",
        json={"value": True},
    )
    assert response.status_code == 403


def test_only_god_user_can_change_roles(
    api_client,
    otp_sender,
) -> None:
    login(api_client, otp_sender, "+15551234567")
    api_client.post("/api/v1/auth/logout")
    login(api_client, otp_sender, "+15550000000")
    target = api_client.get("/api/v1/admin/users?search=15551234567").json()["items"][0]
    promoted = api_client.patch(
        f"/api/v1/admin/users/{target['id']}/role",
        headers={"Origin": "https://testserver"},
        json={"role": "admin"},
    )
    assert promoted.status_code == 200
    api_client.post("/api/v1/auth/logout")
    login(api_client, otp_sender, "+15551234567")
    forbidden = api_client.patch(
        f"/api/v1/admin/users/{target['id']}/role",
        headers={"Origin": "https://testserver"},
        json={"role": "user"},
    )
    assert forbidden.status_code == 403


def test_admin_can_manage_provider_metadata_without_secrets(
    api_client,
    otp_sender,
) -> None:
    login(api_client, otp_sender, "+15550000000")
    provider_response = api_client.post(
        "/api/v1/admin/providers",
        headers={"Origin": "https://testserver"},
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
        headers={"Origin": "https://testserver"},
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
        headers={"Origin": "https://testserver"},
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
        headers={"Origin": "https://testserver"},
        json={"value": 0},
    )
    assert invalid.status_code == 422

    rate_policy = api_client.get("/api/v1/admin/rate-limits")
    assert rate_policy.status_code == 200
    updated_policy = api_client.put(
        "/api/v1/admin/rate-limits",
        headers={"Origin": "https://testserver"},
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
        headers={"Origin": "https://testserver"},
        json={"value": 25},
    )
    assert valid.status_code == 200
    assert valid.json()["value"] == 25
    audit = api_client.get("/api/v1/admin/audit").json()
    assert any(event["action"] == "setting.updated" for event in audit)
