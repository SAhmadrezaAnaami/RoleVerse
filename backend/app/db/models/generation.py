from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GenerationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generation_runs"
    __table_args__ = (
        UniqueConstraint("user_message_id", name="uq_generation_runs_user_message"),
        CheckConstraint(
            "status IN ('queued', 'streaming', 'complete', 'failed', 'cancelled')",
            name="ck_generation_runs_status",
        ),
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND input_cost_micro >= 0 AND output_cost_micro >= 0 AND total_cost_micro >= 0",
            name="ck_generation_runs_usage_nonnegative",
        ),
    )

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    assistant_message_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="SET NULL"),
        index=True,
    )
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    usage_available: Mapped[bool] = mapped_column(default=False, nullable=False)
    pricing_available: Mapped[bool] = mapped_column(default=False, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finish_reason: Mapped[str | None] = mapped_column(String(32))
    input_cost_micro: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_cost_micro: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_micro: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
