from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone_masked: str
    display_name: str
    role: Literal["user", "admin"]
    status: Literal["active", "banned"]
    preferred_language: str
    banned_at: datetime | None
    ban_reason: str | None
    last_login_at: datetime | None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserRead]
    total: int
    limit: int
    offset: int


class AdminUserUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    display_name: str | None = Field(default=None, max_length=80)


class AdminRoleUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    role: Literal["user", "admin"]


class AdminBanRequest(BaseModel):
    model_config = {"extra": "forbid"}

    reason: str = Field(min_length=1, max_length=500)


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, Any]
    created_at: datetime


class AdminIdentityRead(BaseModel):
    id: str
    phone_masked: str
    role: Literal["admin"]
    is_god_user: bool
    capabilities: list[str]


class AdminOverviewRead(BaseModel):
    metrics: dict[str, int]
    rate_limit_policy: dict[str, int]
    provider_runtime_mode: str
    recent_audit: list[AuditEventRead]


class ProviderConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    adapter: Literal["mock", "openai-compatible"]
    base_url: str
    status: Literal["enabled", "disabled", "degraded"]
    is_default: bool
    secret_source: Literal["none", "environment"]
    runtime_mode: Literal["mock", "live"] = "mock"
    credential_configured: bool = False
    activation_supported: bool = False
    last_checked_at: datetime | None
    last_error_code: str | None
    created_at: datetime
    updated_at: datetime


class ProviderConnectionCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=2, max_length=80)
    adapter: Literal["mock", "openai-compatible"] = "mock"
    base_url: str = Field(default="", max_length=500)
    status: Literal["enabled", "disabled", "degraded"] = "disabled"
    is_default: bool = False
    secret_source: Literal["none", "environment"] = "none"


class ProviderConnectionUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=80)
    adapter: Literal["mock", "openai-compatible"] | None = None
    base_url: str | None = Field(default=None, max_length=500)
    status: Literal["enabled", "disabled", "degraded"] | None = None
    is_default: bool | None = None
    secret_source: Literal["none", "environment"] | None = None


class ProviderModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    name: str
    display_name: str
    enabled: bool
    context_window: int
    max_output_tokens: int
    input_price_micro_per_million: int
    output_price_micro_per_million: int
    pricing_available: bool
    created_at: datetime
    updated_at: datetime


class ProviderModelCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(min_length=1, max_length=120)
    display_name: str = Field(default="", max_length=120)
    enabled: bool = True
    context_window: int = Field(default=0, ge=0, le=10_000_000)
    max_output_tokens: int = Field(default=512, ge=1, le=8192)
    input_price_micro_per_million: int = Field(default=0, ge=0)
    output_price_micro_per_million: int = Field(default=0, ge=0)
    pricing_available: bool = False


class ProviderModelUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = Field(default=None, min_length=1, max_length=120)
    display_name: str | None = Field(default=None, max_length=120)
    enabled: bool | None = None
    context_window: int | None = Field(default=None, ge=0, le=10_000_000)
    max_output_tokens: int | None = Field(default=None, ge=1, le=8192)
    input_price_micro_per_million: int | None = Field(default=None, ge=0)
    output_price_micro_per_million: int | None = Field(default=None, ge=0)
    pricing_available: bool | None = None


class RateLimitPolicyRead(BaseModel):
    per_user_limit: int
    global_limit: int
    window_seconds: int
    max_output_tokens: int


class RateLimitPolicyUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    per_user_limit: int = Field(ge=1, le=1000)
    global_limit: int = Field(ge=1, le=10000)
    window_seconds: int = Field(ge=1, le=3600)
    max_output_tokens: int = Field(ge=1, le=8192)


class SystemSettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    value: Any
    updated_by: str | None
    created_at: datetime
    updated_at: datetime


class SystemSettingUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    value: Any


class AdminUsageRead(BaseModel):
    run_id: str
    user_id: str
    provider_name: str
    model_name: str
    status: str
    input_tokens: int
    output_tokens: int
    input_cost_micro: int
    output_cost_micro: int
    total_cost_micro: int
    usage_available: bool
    pricing_available: bool
    finish_reason: str | None
    created_at: datetime


class AdminUsageListResponse(BaseModel):
    items: list[AdminUsageRead]
