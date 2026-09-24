from alembic import op
import sqlalchemy as sa

revision = "0002_characters_chats"
down_revision = "0001_data_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "characters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("tagline", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("persona", sa.Text(), nullable=False, server_default=""),
        sa.Column("soul", sa.Text(), nullable=False, server_default=""),
        sa.Column("backstory", sa.Text(), nullable=False, server_default=""),
        sa.Column("greeting", sa.Text(), nullable=False, server_default=""),
        sa.Column("sample_reply", sa.Text(), nullable=False, server_default=""),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("accent_start", sa.String(length=16), nullable=False, server_default="#7c3aed"),
        sa.Column("accent_end", sa.String(length=16), nullable=False, server_default="#ec4899"),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("translations", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False, server_default="General"),
        sa.Column("default_language", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_characters_created_by_users", ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_characters_status"),
        sa.CheckConstraint("default_language IN ('en', 'fa')", name="ck_characters_language"),
        sa.PrimaryKeyConstraint("id", name="pk_characters"),
        sa.UniqueConstraint("slug", name="uq_characters_slug"),
    )
    op.create_index("ix_characters_slug", "characters", ["slug"])
    op.create_index("ix_characters_name", "characters", ["name"])
    op.create_index("ix_characters_category", "characters", ["category"])
    op.create_index("ix_characters_status", "characters", ["status"])
    op.create_index("ix_characters_is_featured", "characters", ["is_featured"])
    op.create_index("ix_characters_created_by", "characters", ["created_by"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("character_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False, server_default="New conversation"),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_conversations_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], name="fk_conversations_character_id_characters", ondelete="RESTRICT"),
        sa.CheckConstraint("locale IN ('en', 'fa')", name="ck_conversations_locale"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_conversations_status"),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_character_id", "conversations", ["character_id"])
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_conversations_last_message_at", "conversations", ["last_message_at"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="complete"),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("client_request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name="fk_messages_conversation_id_conversations", ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_messages_role"),
        sa.CheckConstraint("status IN ('queued', 'streaming', 'complete', 'failed', 'cancelled', 'deleted')", name="ck_messages_status"),
        sa.CheckConstraint("position >= 1", name="ck_messages_position"),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.UniqueConstraint("conversation_id", "client_request_id", name="uq_messages_request"),
        sa.UniqueConstraint("conversation_id", "position", name="uq_messages_position"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_status", "messages", ["status"])
    op.create_index("ix_messages_client_request_id", "messages", ["client_request_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_client_request_id", table_name="messages")
    op.drop_index("ix_messages_status", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_last_message_at", table_name="conversations")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_index("ix_conversations_character_id", table_name="conversations")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_characters_created_by", table_name="characters")
    op.drop_index("ix_characters_is_featured", table_name="characters")
    op.drop_index("ix_characters_status", table_name="characters")
    op.drop_index("ix_characters_category", table_name="characters")
    op.drop_index("ix_characters_name", table_name="characters")
    op.drop_index("ix_characters_slug", table_name="characters")
    op.drop_table("characters")
