from alembic import op
import sqlalchemy as sa

revision = "0003_generation_runs"
down_revision = "0002_characters_chats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("source", sa.String(length=16), nullable=False, server_default="user"),
    )
    op.execute(
        "UPDATE messages SET source = CASE "
        "WHEN role = 'user' THEN 'user' "
        "WHEN role = 'system' THEN 'system' "
        "WHEN position = 1 THEN 'greeting' "
        "ELSE 'preview' END"
    )
    with op.batch_alter_table("messages") as batch_op:
        batch_op.create_check_constraint(
            "ck_messages_source",
            "source IN ('user', 'greeting', 'preview', 'generation', 'system')",
        )
    op.create_table(
        "generation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("user_message_id", sa.String(length=36), nullable=False),
        sa.Column("assistant_message_id", sa.String(length=36), nullable=True),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("usage_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pricing_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finish_reason", sa.String(length=32), nullable=True),
        sa.Column("input_cost_micro", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_cost_micro", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cost_micro", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name="fk_generation_runs_conversation_id_conversations", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_message_id"], ["messages.id"], name="fk_generation_runs_user_message_id_messages", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assistant_message_id"], ["messages.id"], name="fk_generation_runs_assistant_message_id_messages", ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('queued', 'streaming', 'complete', 'failed', 'cancelled')", name="ck_generation_runs_status"),
        sa.CheckConstraint("input_tokens >= 0 AND output_tokens >= 0 AND input_cost_micro >= 0 AND output_cost_micro >= 0 AND total_cost_micro >= 0", name="ck_generation_runs_usage_nonnegative"),
        sa.PrimaryKeyConstraint("id", name="pk_generation_runs"),
        sa.UniqueConstraint("user_message_id", name="uq_generation_runs_user_message"),
    )
    op.create_index("ix_generation_runs_conversation_id", "generation_runs", ["conversation_id"])
    op.create_index("ix_generation_runs_user_message_id", "generation_runs", ["user_message_id"])
    op.create_index("ix_generation_runs_assistant_message_id", "generation_runs", ["assistant_message_id"])
    op.create_index("ix_generation_runs_status", "generation_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_generation_runs_status", table_name="generation_runs")
    op.drop_index("ix_generation_runs_assistant_message_id", table_name="generation_runs")
    op.drop_index("ix_generation_runs_user_message_id", table_name="generation_runs")
    op.drop_index("ix_generation_runs_conversation_id", table_name="generation_runs")
    op.drop_table("generation_runs")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("ck_messages_source", type_="check")
        batch_op.drop_column("source")
