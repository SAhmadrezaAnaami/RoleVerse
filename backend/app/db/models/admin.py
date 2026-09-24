from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProviderConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "provider_connections"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_provider_connections_slug"),
        CheckConstraint(
            "adapter IN ('mock', 'openai-compatible')",
            name="ck_provider_connections_adapter",
        ),
        CheckConstraint(
            "status IN ('enabled', 'disabled', 'degraded')",
            name="ck_provider_connections_status",
        ),
        CheckConstraint(
            "secret_source IN ('none', 'environment', 'secret_manager')",
            name="ck_provider_connections_secret_source",
        ),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    adapter: Mapped[str] = mapped_column(String(40), default="mock", nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="disabled", index=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    secret_source: Mapped[str] = mapped_column(String(32), default="none", nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )


class ProviderModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "provider_models"
    __table_args__ = (
        UniqueConstraint("provider_id", "name", name="uq_provider_models_provider_name"),
        CheckConstraint("context_window >= 0", name="ck_provider_models_context_window"),
        CheckConstraint("max_output_tokens >= 1", name="ck_provider_models_max_output_tokens"),
        CheckConstraint(
            "input_price_micro_per_million >= 0 AND output_price_micro_per_million >= 0",
            name="ck_provider_models_prices_nonnegative",
        ),
    )

    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("provider_connections.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    context_window: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=512, nullable=False)
    input_price_micro_per_million: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_price_micro_per_million: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pricing_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SystemSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "system_settings"
    __table_args__ = (
        UniqueConstraint("key", name="uq_system_settings_key"),
    )

    key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    value: Mapped[dict[str, object] | list[object] | str | int | float | bool | None] = mapped_column(
        JSON,
        nullable=False,
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('user.banned', 'user.unbanned', 'user.role_changed', 'provider.created', 'provider.updated', 'model.created', 'model.updated', 'setting.updated', 'rate_limit.updated', 'rate_limit.reset')",
            name="ck_audit_events_action",
        ),
    )

    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
