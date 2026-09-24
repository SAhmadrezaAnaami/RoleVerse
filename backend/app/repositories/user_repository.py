from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


class UserRepository:
    def get_by_phone(self, session: Session, phone: str) -> User | None:
        statement = select(User).where(User.phone == phone)
        return session.scalar(statement)

    def get_by_id(self, session: Session, user_id: str) -> User | None:
        return session.get(User, user_id)

    def create(
        self,
        session: Session,
        phone: str,
        display_name: str = "",
        preferred_language: str = "en",
        role: str = "user",
    ) -> User:
        user = User(
            phone=phone,
            display_name=display_name,
            preferred_language=preferred_language,
            role=role,
        )
        session.add(user)
        session.flush()
        return user

    def set_role(self, session: Session, user: User, role: str) -> None:
        user.role = role

    def touch_login(self, session: Session, user: User, timestamp: datetime) -> None:
        user.last_login_at = timestamp
