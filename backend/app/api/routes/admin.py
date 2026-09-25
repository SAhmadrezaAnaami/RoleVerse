from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import Settings, get_settings
from app.core.phone import mask_phone, normalize_phone
from app.api.deps import (
    get_admin_service,
    get_admin_user,
    get_god_admin,
    get_rate_limiter,
    require_csrf,
    require_same_origin,
)
from app.schemas.admin import (
    AdminBanRequest,
    AdminIdentityRead,
    AdminOverviewRead,
    AdminRoleUpdateRequest,
    AdminUsageListResponse,
    AdminUsageRead,
    AdminUserListResponse,
    AdminUserRead,
    AdminUserUpdateRequest,
    AuditEventRead,
    ProviderConnectionCreateRequest,
    ProviderConnectionRead,
    ProviderConnectionUpdateRequest,
    ProviderModelCreateRequest,
    ProviderModelRead,
    ProviderModelUpdateRequest,
    RateLimitPolicyRead,
    RateLimitPolicyUpdateRequest,
    SystemSettingRead,
    SystemSettingUpdateRequest,
)
from app.services import (
    AdminConflictError,
    AdminInputError,
    AdminNotFoundError,
    AdminService,
    InMemoryRateLimiter,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_same_origin), Depends(require_csrf)],
)


def admin_user_data(user) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        phone_masked=mask_phone(user.phone),
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        preferred_language=user.preferred_language,
        banned_at=user.banned_at,
        ban_reason=user.ban_reason,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def redacted_provider_endpoint(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.hostname:
        return ""
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"


def provider_data(provider, settings: Settings) -> ProviderConnectionRead:
    runtime_mode = "live" if (
        settings.live_provider_enabled
        and provider.is_default
        and provider.adapter == "openai-compatible"
        and provider.base_url == settings.openai_base_url
    ) else "mock"
    return ProviderConnectionRead.model_validate(provider).model_copy(
        update={
            "base_url": redacted_provider_endpoint(provider.base_url),
            "runtime_mode": runtime_mode,
            "credential_configured": provider.secret_source in {"environment", "secret_manager"},
            "activation_supported": False,
        }
    )


def map_admin_error(error: Exception) -> HTTPException:
    if isinstance(error, AdminNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, AdminConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


@router.get("/me", response_model=AdminIdentityRead)
async def admin_identity(
    admin=Depends(get_admin_user),
    settings: Settings = Depends(get_settings),
) -> AdminIdentityRead:
    try:
        is_god_user = bool(settings.god_user_phone) and normalize_phone(settings.god_user_phone) == normalize_phone(admin.phone)
    except ValueError:
        is_god_user = False
    capabilities = ["users.read", "providers.read", "usage.read", "settings.read", "audit.read"]
    if is_god_user:
        capabilities.extend(["users.manage_roles", "providers.manage", "settings.manage"])
    return AdminIdentityRead(
        id=admin.id,
        phone_masked=mask_phone(admin.phone),
        role="admin",
        is_god_user=is_god_user,
        capabilities=capabilities,
    )


@router.get("/overview", response_model=AdminOverviewRead)
async def overview(
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AdminOverviewRead:
    del admin
    data = service.overview()
    return AdminOverviewRead(
        metrics=data["metrics"],
        rate_limit_policy=data["rate_limit_policy"],
        provider_runtime_mode=data["provider_runtime_mode"],
        recent_audit=[AuditEventRead.model_validate(event) for event in data["recent_audit"]],
    )


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    search: str = Query(default="", max_length=80),
    role: Literal["user", "admin"] | None = None,
    user_status: Literal["active", "banned"] | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AdminUserListResponse:
    del admin
    users, total = service.list_users(search, role, user_status, limit, offset)
    return AdminUserListResponse(
        items=[admin_user_data(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/users/{user_id}", response_model=AdminUserRead)
async def update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AdminUserRead:
    try:
        user = service.update_user_profile(
            admin,
            user_id,
            payload.display_name,
        )
    except (AdminNotFoundError, AdminConflictError, AdminInputError) as error:
        raise map_admin_error(error) from error
    return admin_user_data(user)


@router.patch("/users/{user_id}/role", response_model=AdminUserRead)
async def change_user_role(
    user_id: str,
    payload: AdminRoleUpdateRequest,
    admin=Depends(get_god_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminUserRead:
    try:
        user = service.change_role(admin, user_id, payload.role)
    except (AdminNotFoundError, AdminConflictError, AdminInputError) as error:
        raise map_admin_error(error) from error
    return admin_user_data(user)


@router.post("/users/{user_id}/ban", response_model=AdminUserRead)
async def ban_user(
    user_id: str,
    payload: AdminBanRequest,
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AdminUserRead:
    try:
        user = service.ban_user(admin, user_id, payload.reason)
    except (AdminNotFoundError, AdminConflictError, AdminInputError) as error:
        raise map_admin_error(error) from error
    return admin_user_data(user)


@router.post("/users/{user_id}/unban", response_model=AdminUserRead)
async def unban_user(
    user_id: str,
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AdminUserRead:
    try:
        user = service.unban_user(admin, user_id)
    except (AdminNotFoundError, AdminConflictError, AdminInputError) as error:
        raise map_admin_error(error) from error
    return admin_user_data(user)


@router.post("/users/{user_id}/revoke-sessions", response_model=AdminUserRead)
async def revoke_user_sessions(
    user_id: str,
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AdminUserRead:
    try:
        user = service.revoke_sessions(admin, user_id)
    except (AdminNotFoundError, AdminConflictError, AdminInputError) as error:
        raise map_admin_error(error) from error
    return admin_user_data(user)


@router.get("/providers", response_model=list[ProviderConnectionRead])
async def list_providers(
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> list[ProviderConnectionRead]:
    del admin
    return [provider_data(provider, service.settings) for provider in service.list_providers()]


@router.post("/providers", response_model=ProviderConnectionRead, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: ProviderConnectionCreateRequest,
    admin=Depends(get_god_admin),
    service: AdminService = Depends(get_admin_service),
) -> ProviderConnectionRead:
    try:
        provider = service.create_provider(admin, payload.model_dump())
    except (AdminConflictError, AdminInputError) as error:
        raise map_admin_error(error) from error
    return provider_data(provider, service.settings)


@router.patch("/providers/{provider_id}", response_model=ProviderConnectionRead)
async def update_provider(
    provider_id: str,
    payload: ProviderConnectionUpdateRequest,
    admin=Depends(get_god_admin),
    service: AdminService = Depends(get_admin_service),
) -> ProviderConnectionRead:
    try:
        provider = service.update_provider(
            admin,
            provider_id,
            payload.model_dump(exclude_unset=True),
        )
    except (AdminNotFoundError, AdminConflictError, AdminInputError) as error:
        raise map_admin_error(error) from error
    return provider_data(provider, service.settings)


@router.get("/providers/{provider_id}/models", response_model=list[ProviderModelRead])
async def list_models(
    provider_id: str,
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> list[ProviderModelRead]:
    del admin
    try:
        models = service.list_models(provider_id)
    except AdminNotFoundError as error:
        raise map_admin_error(error) from error
    return [ProviderModelRead.model_validate(model) for model in models]


@router.post("/providers/{provider_id}/models", response_model=ProviderModelRead, status_code=status.HTTP_201_CREATED)
async def create_model(
    provider_id: str,
    payload: ProviderModelCreateRequest,
    admin=Depends(get_god_admin),
    service: AdminService = Depends(get_admin_service),
) -> ProviderModelRead:
    try:
        model = service.create_model(admin, provider_id, payload.model_dump())
    except (AdminNotFoundError, AdminConflictError, AdminInputError) as error:
        raise map_admin_error(error) from error
    return ProviderModelRead.model_validate(model)


@router.patch("/providers/{provider_id}/models/{model_id}", response_model=ProviderModelRead)
async def update_model(
    provider_id: str,
    model_id: str,
    payload: ProviderModelUpdateRequest,
    admin=Depends(get_god_admin),
    service: AdminService = Depends(get_admin_service),
) -> ProviderModelRead:
    try:
        model = service.update_model(
            admin,
            provider_id,
            model_id,
            payload.model_dump(exclude_unset=True),
        )
    except (AdminNotFoundError, AdminConflictError, AdminInputError) as error:
        raise map_admin_error(error) from error
    return ProviderModelRead.model_validate(model)


@router.get("/usage", response_model=AdminUsageListResponse)
async def usage(
    limit: int = Query(default=50, ge=1, le=200),
    start: datetime | None = None,
    end: datetime | None = None,
    user_id: str | None = Query(default=None, max_length=36),
    provider: str | None = Query(default=None, max_length=80),
    model: str | None = Query(default=None, max_length=120),
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AdminUsageListResponse:
    del admin
    items = []
    for run, user_id in service.usage(limit, start, end, user_id, provider, model):
        items.append(
            AdminUsageRead(
                run_id=run.id,
                user_id=user_id,
                provider_name=run.provider_name,
                model_name=run.model_name,
                status=run.status,
                input_tokens=run.input_tokens,
                output_tokens=run.output_tokens,
                input_cost_micro=run.input_cost_micro,
                output_cost_micro=run.output_cost_micro,
                total_cost_micro=run.total_cost_micro,
                usage_available=run.usage_available,
                pricing_available=run.pricing_available,
                finish_reason=run.finish_reason,
                created_at=run.created_at,
            )
        )
    return AdminUsageListResponse(items=items)


@router.get("/rate-limits", response_model=RateLimitPolicyRead)
async def get_rate_limits(
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> RateLimitPolicyRead:
    del admin
    return RateLimitPolicyRead(**service.rate_limit_policy())


@router.put("/rate-limits", response_model=RateLimitPolicyRead)
async def update_rate_limits(
    payload: RateLimitPolicyUpdateRequest,
    admin=Depends(get_god_admin),
    service: AdminService = Depends(get_admin_service),
    limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> RateLimitPolicyRead:
    try:
        policy = service.update_rate_limit(admin, payload.model_dump())
    except AdminInputError as error:
        raise map_admin_error(error) from error
    limiter.clear_prefix("generation:")
    return RateLimitPolicyRead(**policy)


@router.post("/rate-limits/reset", response_model=RateLimitPolicyRead)
async def reset_rate_limits(
    admin=Depends(get_god_admin),
    service: AdminService = Depends(get_admin_service),
    limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> RateLimitPolicyRead:
    try:
        service.reset_rate_limit(admin)
    except AdminInputError as error:
        raise map_admin_error(error) from error
    limiter.clear_prefix("generation:")
    return RateLimitPolicyRead(**service.rate_limit_policy())


@router.get("/settings", response_model=list[SystemSettingRead])
async def list_settings(
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> list[SystemSettingRead]:
    del admin
    return [SystemSettingRead.model_validate(setting) for setting in service.list_settings()]


@router.patch("/settings/{key}", response_model=SystemSettingRead)
async def update_setting(
    key: str,
    payload: SystemSettingUpdateRequest,
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
    limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> SystemSettingRead:
    try:
        setting = service.update_setting(admin, key, payload.value)
    except AdminInputError as error:
        raise map_admin_error(error) from error
    limiter.clear_prefix("generation:")
    return SystemSettingRead.model_validate(setting)


@router.get("/audit", response_model=list[AuditEventRead])
@router.get("/audit-events", response_model=list[AuditEventRead])
async def audit(
    limit: int = Query(default=50, ge=1, le=200),
    admin=Depends(get_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> list[AuditEventRead]:
    del admin
    return [AuditEventRead.model_validate(event) for event in service.audit(limit)]
