from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Character, Conversation, Message


class ConversationRepository:
    def list_for_user(self, session: Session, user_id: str) -> list[Conversation]:
        statement = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(session.scalars(statement))

    def get_for_user(
        self,
        session: Session,
        conversation_id: str,
        user_id: str,
    ) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        return session.scalar(statement)

    def get_character(self, session: Session, character_id: str) -> Character | None:
        return session.get(Character, character_id)

    def create(
        self,
        session: Session,
        user_id: str,
        character_id: str,
        title: str,
        locale: str,
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            character_id=character_id,
            title=title,
            locale=locale,
        )
        session.add(conversation)
        session.flush()
        return conversation

    def message_count(self, session: Session, conversation_id: str) -> int:
        statement = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id,
        )
        return session.scalar(statement) or 0

    def last_message(self, session: Session, conversation_id: str) -> Message | None:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.position.desc())
            .limit(1)
        )
        return session.scalar(statement)

    def list_messages(
        self,
        session: Session,
        conversation_id: str,
        limit: int,
    ) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.position.desc())
            .limit(limit)
        )
        return list(reversed(list(session.scalars(statement))))

    def get_message_by_request(
        self,
        session: Session,
        conversation_id: str,
        client_request_id: str,
    ) -> Message | None:
        statement = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.client_request_id == client_request_id,
        )
        return session.scalar(statement)

    def get_message_at_position(
        self,
        session: Session,
        conversation_id: str,
        position: int,
    ) -> Message | None:
        statement = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.position == position,
        )
        return session.scalar(statement)

    def max_position(self, session: Session, conversation_id: str) -> int:
        statement = select(func.max(Message.position)).where(
            Message.conversation_id == conversation_id,
        )
        return session.scalar(statement) or 0

    def add_message(
        self,
        session: Session,
        conversation_id: str,
        role: str,
        content: str,
        position: int,
        client_request_id: str | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            position=position,
            client_request_id=client_request_id,
        )
        session.add(message)
        session.flush()
        return message

    def touch(self, conversation: Conversation, timestamp: datetime) -> None:
        conversation.last_message_at = timestamp
        conversation.updated_at = timestamp
