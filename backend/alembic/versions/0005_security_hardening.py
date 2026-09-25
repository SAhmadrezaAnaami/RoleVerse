from alembic import op
import sqlalchemy as sa

revision = "0005_security_hardening"
down_revision = "0004_admin_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column(
        "auth_sessions",
        sa.Column("auth_epoch", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "users",
        sa.Column("auth_epoch", sa.Integer(), nullable=False, server_default="1"),
    )
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.drop_constraint("ck_audit_events_action", type_="check")
        batch_op.create_check_constraint(
            "ck_audit_events_action",
            "action IN ('user.banned', 'user.unbanned', 'user.sessions_revoked', 'user.role_changed', 'provider.created', 'provider.updated', 'model.created', 'model.updated', 'setting.updated', 'rate_limit.updated', 'rate_limit.reset')",
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.drop_constraint("ck_audit_events_action", type_="check")
        batch_op.create_check_constraint(
            "ck_audit_events_action",
            "action IN ('user.banned', 'user.unbanned', 'user.role_changed', 'provider.created', 'provider.updated', 'model.created', 'model.updated', 'setting.updated', 'rate_limit.updated', 'rate_limit.reset')",
        )
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("auth_epoch")
    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.drop_column("auth_epoch")
        batch_op.drop_column("csrf_token_hash")
