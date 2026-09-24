import re
from datetime import datetime
from typing import Any

from app.core.config import Settings
from app.db.base import utc_now
from app.db.models import ProviderConnection, ProviderModel, SystemSetting, User
from app.providers.base import ProviderConfigurationError
from app.providers.config import validate_provider_url
from app.repositories import AdminRepository, AuthRepository
from app.services.runtime_settings_service import RuntimeSettingsService

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,78}$")
SETTING_VALIDATORS: dict[str, tuple[type, tuple[int, int] | None]] = {
    "generation_rate_limit_per_user": (int, (1, 1000)),
    "generation_rate_limit_global": (int, (1, 10000)),
    "generation_rate_limit_window_seconds": (int, (1, 3600)),
    "generation_max_output_tokens": (int, (1, 8192)),
    "maintenance_mode": (bool, None),
}


class AdminNotFoundError(Exception):
    pass


class AdminConflictError(Exception):
    pass


class AdminInputError(Exception):
    pass


class AdminService:
    def __init__(self, session, settings: Settings, clock=utc_now) -> None:
        self.session = session
        self.settings = settings
        self.clock = clock
        self.repository = AdminRepository()
        self.auth_repository = AuthRepository()

    def overview(self) -> dict[str, Any]:
        policy = RuntimeSettingsService(self.session, self.settings).generation_policy()
        default_provider = next(
            (provider for provider in self.list_providers() if provider.is_default),
            None,
        )
        runtime_mode = "mock" if default_provider is None or default_provider.adapter == "mock" else "live"
        return {
            "metrics": self.repository.overview_metrics(self.session),
            "rate_limit_policy": {
                "per_user_limit": policy.per_user_limit,
                "global_limit": policy.global_limit,
                "window_seconds": policy.window_seconds,
                "max_output_tokens": policy.max_output_tokens,
            },
            "provider_runtime_mode": runtime_mode,
            "recent_audit": self.repository.list_audit_events(self.session, limit=8),
        }

    def list_users(
        self,
        search: str,
        role: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[User], int]:
        users = self.repository.list_users(
            self.session,
            search=search,
            role=role,
            status=status,
            limit=limit,
            offset=offset,
        )
        total = self.repository.count_users(
            self.session,
            search=search,
            role=role,
            status=status,
        )
        return users, total

    def update_user_profile(
        self,
        actor: User,
        user_id: str,
        display_name: str | None,
    ) -> User:
        self._require_admin(actor)
        user = self.repository.get_user(self.session, user_id)
        if user is None:
            raise AdminNotFoundError("User not found.")
        if display_name is not None:
            user.display_name = display_name.strip()[:80]
        user.updated_at = self.clock()
        self.session.commit()
        return user

    def change_role(self, actor: User, user_id: str, role: str) -> User:
        if not self._is_god_user(actor):
            raise AdminInputError("God-user access is required.")
        user = self.repository.get_user(self.session, user_id)
        if user is None:
            raise AdminNotFoundError("User not found.")
        if user.id == actor.id or self._is_god_user(user):
            raise AdminInputError("The god user cannot change their own role.")
        if role not in {"user", "admin"}:
            raise AdminInputError("Role must be user or admin.")
        if user.role == "admin" and role == "user" and self.repository.count_active_admins(self.session) <= 1:
            raise AdminInputError("The last active administrator cannot be demoted.")
        if user.role != role:
            user.role = role
            user.updated_at = self.clock()
            self._audit(
                actor.id,
                "user.role_changed",
                "user",
                user.id,
                {"role": role},
            )
            self.session.commit()
        return user

    def ban_user(self, actor: User, user_id: str, reason: str) -> User:
        self._require_admin(actor)
        user = self.repository.get_user(self.session, user_id)
        if user is None:
            raise AdminNotFoundError("User not found.")
        if user.id == actor.id or self._is_god_user(user):
            raise AdminInputError("This account cannot be banned.")
        if user.role == "admin" and not self._is_god_user(actor):
            raise AdminInputError("God-user access is required to ban an administrator.")
        if user.status == "banned":
            return user
        now = self.clock()
        user.status = "banned"
        user.banned_at = now
        user.ban_reason = reason.strip()[:500]
        user.updated_at = now
        self.auth_repository.revoke_user_sessions(self.session, user.id, now)
        self.repository.cancel_active_generations_for_user(self.session, user.id, now)
        self._audit(
            actor.id,
            "user.banned",
            "user",
            user.id,
            {"reason": "administrator_action"},
        )
        self.session.commit()
        return user

    def unban_user(self, actor: User, user_id: str) -> User:
        self._require_admin(actor)
        user = self.repository.get_user(self.session, user_id)
        if user is None:
            raise AdminNotFoundError("User not found.")
        if user.id == actor.id or self._is_god_user(user):
            raise AdminInputError("This account cannot be changed.")
        if user.role == "admin" and not self._is_god_user(actor):
            raise AdminInputError("God-user access is required to unban an administrator.")
        if user.status == "active":
            return user
        user.status = "active"
        user.banned_at = None
        user.ban_reason = None
        user.updated_at = self.clock()
        self._audit(
            actor.id,
            "user.unbanned",
            "user",
            user.id,
            {},
        )
        self.session.commit()
        return user

    def list_providers(self) -> list[ProviderConnection]:
        return self.repository.list_provider_connections(self.session)

    def create_provider(
        self,
        actor: User,
        values: dict[str, Any],
    ) -> ProviderConnection:
        if not self._is_god_user(actor):
            raise AdminInputError("God-user access is required for provider configuration.")
        normalized = self._validate_provider_values(values)
        if self._provider_slug_exists(normalized["slug"]):
            raise AdminConflictError("Provider slug already exists.")
        if normalized["is_default"]:
            self._clear_default_provider()
        provider = self.repository.create_provider_connection(
            self.session,
            actor_id=actor.id,
            **normalized,
        )
        self._audit(
            actor.id,
            "provider.created",
            "provider",
            provider.id,
            {"slug": provider.slug, "adapter": provider.adapter},
        )
        self.session.commit()
        return provider

    def update_provider(
        self,
        actor: User,
        provider_id: str,
        values: dict[str, Any],
    ) -> ProviderConnection:
        provider = self.repository.get_provider_connection(self.session, provider_id)
        if provider is None:
            raise AdminNotFoundError("Provider not found.")
        if values.get("slug", provider.slug) != provider.slug or values.get("adapter", provider.adapter) != provider.adapter:
            raise AdminInputError("Provider identity fields cannot be changed.")
        merged = {
            "name": values.get("name", provider.name),
            "slug": values.get("slug", provider.slug),
            "adapter": values.get("adapter", provider.adapter),
            "base_url": values.get("base_url", provider.base_url),
            "status": values.get("status", provider.status),
            "is_default": values.get("is_default", provider.is_default),
            "secret_source": values.get("secret_source", provider.secret_source),
        }
        if not self._is_god_user(actor):
            raise AdminInputError("God-user access is required for provider configuration.")
        normalized = self._validate_provider_values(merged)
        if normalized["slug"] != provider.slug and self._provider_slug_exists(normalized["slug"]):
            raise AdminConflictError("Provider slug already exists.")
        if normalized["is_default"]:
            self._clear_default_provider(exclude_id=provider.id)
        self.repository.update_provider_connection(provider, normalized)
        self._audit(
            actor.id,
            "provider.updated",
            "provider",
            provider.id,
            {"slug": provider.slug, "status": provider.status},
        )
        self.session.commit()
        return provider

    def list_models(self, provider_id: str) -> list[ProviderModel]:
        self._require_provider(provider_id)
        return self.repository.list_provider_models(self.session, provider_id)

    def create_model(
        self,
        actor: User,
        provider_id: str,
        values: dict[str, Any],
    ) -> ProviderModel:
        self._require_admin(actor)
        self._require_provider(provider_id)
        normalized = self._validate_model_values(values)
        if self.repository.get_provider_model_by_name(self.session, provider_id, normalized["name"]):
            raise AdminConflictError("Model name already exists for this provider.")
        model = self.repository.create_provider_model(
            self.session,
            provider_id,
            normalized,
        )
        self._audit(
            actor.id,
            "model.created",
            "model",
            model.id,
            {"provider_id": provider_id, "name": model.name},
        )
        self.session.commit()
        return model

    def update_model(
        self,
        actor: User,
        provider_id: str,
        model_id: str,
        values: dict[str, Any],
    ) -> ProviderModel:
        self._require_admin(actor)
        model = self.repository.get_provider_model(self.session, provider_id, model_id)
        if model is None:
            raise AdminNotFoundError("Model not found.")
        if values.get("name", model.name) != model.name:
            raise AdminInputError("Model identity fields cannot be changed.")
        normalized = self._validate_model_values({
            "name": values.get("name", model.name),
            "display_name": values.get("display_name", model.display_name),
            "enabled": values.get("enabled", model.enabled),
            "context_window": values.get("context_window", model.context_window),
            "max_output_tokens": values.get("max_output_tokens", model.max_output_tokens),
            "input_price_micro_per_million": values.get("input_price_micro_per_million", model.input_price_micro_per_million),
            "output_price_micro_per_million": values.get("output_price_micro_per_million", model.output_price_micro_per_million),
            "pricing_available": values.get("pricing_available", model.pricing_available),
        })
        self.repository.update_provider_model(model, normalized)
        self._audit(
            actor.id,
            "model.updated",
            "model",
            model.id,
            {"provider_id": provider_id, "name": model.name, "enabled": model.enabled},
        )
        self.session.commit()
        return model

    def list_settings(self) -> list[SystemSetting]:
        return [
            setting
            for setting in self.repository.list_settings(self.session)
            if setting.key in SETTING_VALIDATORS
        ]

    def rate_limit_policy(self) -> dict[str, int]:
        policy = RuntimeSettingsService(self.session, self.settings).generation_policy()
        return {
            "per_user_limit": policy.per_user_limit,
            "global_limit": policy.global_limit,
            "window_seconds": policy.window_seconds,
            "max_output_tokens": policy.max_output_tokens,
        }

    def update_rate_limit(self, actor: User, values: dict[str, int]) -> dict[str, int]:
        if not self._is_god_user(actor):
            raise AdminInputError("God-user access is required for rate-limit changes.")
        keys = {
            "per_user_limit": "generation_rate_limit_per_user",
            "global_limit": "generation_rate_limit_global",
            "window_seconds": "generation_rate_limit_window_seconds",
            "max_output_tokens": "generation_max_output_tokens",
        }
        for field, key in keys.items():
            normalized = self._validate_setting(key, values[field])
            self.repository.upsert_setting(self.session, key, normalized, actor.id)
        self._audit(
            actor.id,
            "rate_limit.updated",
            "rate_limit",
            "generation",
            {"keys": sorted(keys.values())},
        )
        self.session.commit()
        return self.rate_limit_policy()

    def reset_rate_limit(self, actor: User) -> None:
        if not self._is_god_user(actor):
            raise AdminInputError("God-user access is required for rate-limit changes.")
        self._audit(
            actor.id,
            "rate_limit.reset",
            "rate_limit",
            "generation",
            {},
        )
        self.session.commit()

    def update_setting(
        self,
        actor: User,
        key: str,
        value: Any,
    ) -> SystemSetting:
        self._require_admin(actor)
        if key.startswith("generation_rate_limit") or key in {"generation_max_output_tokens", "maintenance_mode"}:
            if not self._is_god_user(actor):
                raise AdminInputError("God-user access is required for this setting.")
        normalized = self._validate_setting(key, value)
        setting = self.repository.upsert_setting(
            self.session,
            key,
            normalized,
            actor.id,
        )
        self._audit(
            actor.id,
            "setting.updated",
            "setting",
            setting.id,
            {"key": key},
        )
        self.session.commit()
        return setting

    def usage(
        self,
        limit: int = 50,
        start: datetime | None = None,
        end: datetime | None = None,
        user_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> list[tuple[Any, str]]:
        return self.repository.list_usage_runs(
            self.session,
            limit=limit,
            start=start,
            end=end,
            user_id=user_id,
            provider=provider,
            model=model,
        )

    def audit(self, limit: int = 50) -> list[Any]:
        return self.repository.list_audit_events(self.session, limit=limit)

    def _require_admin(self, user: User) -> None:
        if user.role != "admin" or user.status != "active":
            raise AdminInputError("Administrator access is required.")

    def _is_god_user(self, user: User) -> bool:
        return (
            user.role == "admin"
            and user.status == "active"
            and bool(self.settings.god_user_phone)
            and user.phone == self.settings.god_user_phone
        )

    def _require_provider(self, provider_id: str) -> ProviderConnection:
        provider = self.repository.get_provider_connection(self.session, provider_id)
        if provider is None:
            raise AdminNotFoundError("Provider not found.")
        return provider

    def _provider_slug_exists(self, slug: str) -> bool:
        return any(provider.slug == slug for provider in self.list_providers())

    def _clear_default_provider(self, exclude_id: str | None = None) -> None:
        for provider in self.list_providers():
            if provider.id != exclude_id:
                provider.is_default = False

    def _audit(
        self,
        actor_id: str | None,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any],
    ) -> None:
        self.repository.create_audit_event(
            self.session,
            actor_id,
            action,
            entity_type,
            entity_id,
            details,
            self.clock(),
        )

    def _validate_provider_values(self, values: dict[str, Any]) -> dict[str, Any]:
        name = str(values.get("name", "")).strip()
        slug = str(values.get("slug", "")).strip().lower()
        adapter = str(values.get("adapter", "mock"))
        base_url = str(values.get("base_url", "")).strip()
        status = str(values.get("status", "disabled"))
        secret_source = str(values.get("secret_source", "none"))
        if not name or len(name) > 120:
            raise AdminInputError("Provider name is required.")
        if not SLUG_PATTERN.fullmatch(slug):
            raise AdminInputError("Provider slug must use lowercase letters, numbers, and hyphens.")
        if adapter not in {"mock", "openai-compatible"}:
            raise AdminInputError("Unsupported provider adapter.")
        if status not in {"enabled", "disabled", "degraded"}:
            raise AdminInputError("Unsupported provider status.")
        if secret_source not in {"none", "environment"}:
            raise AdminInputError("Unsupported secret source.")
        if adapter == "openai-compatible":
            if not base_url:
                raise AdminInputError("OpenAI-compatible providers require a base URL.")
            if self.settings.environment.lower() == "production" and not self.settings.provider_allowed_hosts.strip():
                raise AdminInputError("Production provider hosts require an explicit allowlist.")
            allowed_hosts = {
                host.strip().lower().rstrip(".")
                for host in self.settings.provider_allowed_hosts.split(",")
                if host.strip()
            }
            try:
                validate_provider_url(
                    base_url,
                    self.settings.environment,
                    allowed_hosts or None,
                )
            except ProviderConfigurationError as error:
                raise AdminInputError("Provider URL is invalid.") from error
        return {
            "name": name,
            "slug": slug,
            "adapter": adapter,
            "base_url": base_url,
            "status": status,
            "is_default": bool(values.get("is_default", False)),
            "secret_source": secret_source,
        }

    def _validate_model_values(self, values: dict[str, Any]) -> dict[str, Any]:
        name = str(values.get("name", "")).strip()
        display_name = str(values.get("display_name", "")).strip()
        if not name or len(name) > 120:
            raise AdminInputError("Model name is required.")
        if len(display_name) > 120:
            raise AdminInputError("Model display name is too long.")
        try:
            numeric_values = {
                "context_window": int(values.get("context_window", 0)),
                "max_output_tokens": int(values.get("max_output_tokens", 512)),
                "input_price_micro_per_million": int(values.get("input_price_micro_per_million", 0)),
                "output_price_micro_per_million": int(values.get("output_price_micro_per_million", 0)),
                "pricing_available": bool(values.get("pricing_available", False)),
            }
        except (TypeError, ValueError) as error:
            raise AdminInputError("Model limits and prices must be integers.") from error
        if numeric_values["context_window"] < 0 or numeric_values["max_output_tokens"] < 1:
            raise AdminInputError("Model limits cannot be negative.")
        if any(value < 0 for key, value in numeric_values.items() if "price" in key):
            raise AdminInputError("Model prices cannot be negative.")
        return {
            "name": name,
            "display_name": display_name,
            "enabled": bool(values.get("enabled", True)),
            **numeric_values,
        }

    def _validate_setting(self, key: str, value: Any) -> Any:
        if key not in SETTING_VALIDATORS:
            raise AdminInputError("Setting is not editable.")
        expected_type, bounds = SETTING_VALIDATORS[key]
        if expected_type is bool:
            if not isinstance(value, bool):
                raise AdminInputError("Setting value has an invalid type.")
            return value
        if expected_type is int and isinstance(value, bool):
            raise AdminInputError("Setting value has an invalid type.")
        if not isinstance(value, expected_type):
            raise AdminInputError("Setting value has an invalid type.")
        if bounds is not None and not bounds[0] <= value <= bounds[1]:
            raise AdminInputError("Setting value is outside the allowed range.")
        return value
