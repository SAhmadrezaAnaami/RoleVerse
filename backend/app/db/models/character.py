from sqlalchemy import Boolean, CheckConstraint, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Character(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "characters"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_characters_slug"),
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_characters_status"),
        CheckConstraint("default_language IN ('en', 'fa')", name="ck_characters_language"),
    )

    slug: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    tagline: Mapped[str] = mapped_column(String(180), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    persona: Mapped[str] = mapped_column(Text, default="", nullable=False)
    soul: Mapped[str] = mapped_column(Text, default="", nullable=False)
    backstory: Mapped[str] = mapped_column(Text, default="", nullable=False)
    greeting: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sample_reply: Mapped[str] = mapped_column(Text, default="", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    accent_start: Mapped[str] = mapped_column(String(16), default="#7c3aed", nullable=False)
    accent_end: Mapped[str] = mapped_column(String(16), default="#ec4899", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    translations: Mapped[dict[str, dict[str, object]]] = mapped_column(JSON, default=dict, nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="General", index=True, nullable=False)
    default_language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
