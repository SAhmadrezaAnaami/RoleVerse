from alembic import op
import sqlalchemy as sa

revision = "0004_admin_operations"
down_revision = "0003_generation_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_connections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("adapter", sa.String(length=40), nullable=False, server_default="mock"),
        sa.Column("base_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="disabled"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("secret_source", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_provider_connections_created_by_users", ondelete="SET NULL"),
        sa.CheckConstraint("adapter IN ('mock', 'openai-compatible')", name="ck_provider_connections_adapter"),
        sa.CheckConstraint("status IN ('enabled', 'disabled', 'degraded')", name="ck_provider_connections_status"),
        sa.CheckConstraint("secret_source IN ('none', 'environment', 'secret_manager')", name="ck_provider_connections_secret_source"),
        sa.PrimaryKeyConstraint("id", name="pk_provider_connections"),
        sa.UniqueConstraint("slug", name="uq_provider_connections_slug"),
    )
    op.create_index("ix_provider_connections_slug", "provider_connections", ["slug"])
    op.create_index("ix_provider_connections_status", "provider_connections", ["status"])
    op.create_index("ix_provider_connections_is_default", "provider_connections", ["is_default"])
    op.create_index("ix_provider_connections_created_by", "provider_connections", ["created_by"])

    op.create_table(
        "provider_models",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("context_window", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False, server_default="512"),
        sa.Column("input_price_micro_per_million", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_price_micro_per_million", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pricing_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_connections.id"], name="fk_provider_models_provider_id_provider_connections", ondelete="CASCADE"),
        sa.CheckConstraint("context_window >= 0", name="ck_provider_models_context_window"),
        sa.CheckConstraint("max_output_tokens >= 1", name="ck_provider_models_max_output_tokens"),
        sa.CheckConstraint("input_price_micro_per_million >= 0 AND output_price_micro_per_million >= 0", name="ck_provider_models_prices_nonnegative"),
        sa.PrimaryKeyConstraint("id", name="pk_provider_models"),
        sa.UniqueConstraint("provider_id", "name", name="uq_provider_models_provider_name"),
    )
    op.create_index("ix_provider_models_provider_id", "provider_models", ["provider_id"])
    op.create_index("ix_provider_models_enabled", "provider_models", ["enabled"])

    op.create_table(
        "system_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_system_settings_updated_by_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_system_settings"),
        sa.UniqueConstraint("key", name="uq_system_settings_key"),
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"])
    op.create_index("ix_system_settings_updated_by", "system_settings", ["updated_by"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_audit_events_actor_user_id_users", ondelete="SET NULL"),
        sa.CheckConstraint("action IN ('user.banned', 'user.unbanned', 'user.role_changed', 'provider.created', 'provider.updated', 'model.created', 'model.updated', 'setting.updated', 'rate_limit.updated', 'rate_limit.reset')", name="ck_audit_events_action"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_entity_id", table_name="audit_events")
    op.drop_index("ix_audit_events_entity_type", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_user_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_system_settings_updated_by", table_name="system_settings")
    op.drop_index("ix_system_settings_key", table_name="system_settings")
    op.drop_table("system_settings")
    op.drop_index("ix_provider_models_enabled", table_name="provider_models")
    op.drop_index("ix_provider_models_provider_id", table_name="provider_models")
    op.drop_table("provider_models")
    op.drop_index("ix_provider_connections_created_by", table_name="provider_connections")
    op.drop_index("ix_provider_connections_is_default", table_name="provider_connections")
    op.drop_index("ix_provider_connections_status", table_name="provider_connections")
    op.drop_index("ix_provider_connections_slug", table_name="provider_connections")
    op.drop_table("provider_connections")
