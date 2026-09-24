from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Character


class CharacterRepository:
    def list_published(
        self,
        session: Session,
        search: str | None,
        category: str | None,
        limit: int,
        offset: int,
    ) -> list[Character]:
        statement = select(Character).where(Character.status == "published")
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Character.name.ilike(pattern),
                    Character.tagline.ilike(pattern),
                    Character.description.ilike(pattern),
                )
            )
        if category:
            statement = statement.where(Character.category == category)
        statement = statement.order_by(
            Character.is_featured.desc(),
            Character.name.asc(),
        ).offset(offset).limit(limit)
        return list(session.scalars(statement))

    def get_published_by_slug(self, session: Session, slug: str) -> Character | None:
        statement = select(Character).where(
            Character.slug == slug,
            Character.status == "published",
        )
        return session.scalar(statement)

    def get_by_id(self, session: Session, character_id: str) -> Character | None:
        return session.get(Character, character_id)
