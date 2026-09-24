from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.db.models import Character, Conversation, Message
from app.repositories import ConversationRepository
from app.services.character_service import CharacterService


class ConversationNotFoundError(Exception):
    pass


class ConversationInactiveError(Exception):
    pass


class IdempotencyConflictError(Exception):
    pass


@dataclass
class ConversationBundle:
    conversation: Conversation
    character: Character


@dataclass
class MessagePair:
    user_message: Message
    assistant_message: Message


class ConversationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ConversationRepository()
        self.character_service = CharacterService(session)

    def localized_character(self, character: Character, locale: str) -> dict[str, Any]:
        return self.character_service.localized_values(character, locale)

    def list_for_user(self, user_id: str) -> list[ConversationBundle]:
        bundles = []
        for conversation in self.repository.list_for_user(self.session, user_id):
            character = self.repository.get_character(self.session, conversation.character_id)
            if character is not None:
                bundles.append(ConversationBundle(conversation, character))
        return bundles

    def create(
        self,
        user_id: str,
        character_slug: str,
        title: str | None,
        locale: str,
    ) -> ConversationBundle:
        character_model = self.character_service.get_character_model(character_slug)
        character = self.localized_character(character_model, locale)
        conversation_title = title.strip() if title and title.strip() else f"Chat with {character['name']}"
        conversation = self.repository.create(
            self.session,
            user_id,
            character_model.id,
            conversation_title,
            locale,
        )
        now = utc_now()
        conversation.created_at = now
        conversation.updated_at = now
        greeting = self.repository.add_message(
            self.session,
            conversation.id,
            "assistant",
            character["greeting"],
            1,
        )
        greeting.created_at = now
        greeting.updated_at = now
        conversation.last_message_at = now
        self.session.commit()
        return ConversationBundle(conversation, character_model)

    def summary_fields(self, bundle: ConversationBundle) -> dict[str, Any]:
        last_message = self.repository.last_message(
            self.session,
            bundle.conversation.id,
        )
        return {
            "last_message_preview": last_message.content[:120] if last_message else "",
            "message_count": self.repository.message_count(
                self.session,
                bundle.conversation.id,
            ),
        }

    def get_for_user(self, conversation_id: str, user_id: str) -> ConversationBundle:
        conversation = self.repository.get_for_user(
            self.session,
            conversation_id,
            user_id,
        )
        if conversation is None:
            raise ConversationNotFoundError("Conversation not found.")
        character = self.repository.get_character(self.session, conversation.character_id)
        if character is None:
            raise ConversationNotFoundError("Conversation character not found.")
        return ConversationBundle(conversation, character)

    def list_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: int,
    ) -> list[Message]:
        self.get_for_user(conversation_id, user_id)
        return self.repository.list_messages(self.session, conversation_id, limit)

    def append_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        client_request_id: str | None,
    ) -> MessagePair:
        bundle = self.get_for_user(conversation_id, user_id)
        if bundle.conversation.status != "active":
            raise ConversationInactiveError("Conversation is not active.")
        if client_request_id:
            existing = self.repository.get_message_by_request(
                self.session,
                conversation_id,
                client_request_id,
            )
            if existing is not None:
                if existing.content != content:
                    raise IdempotencyConflictError("The request identifier was already used with different content.")
                assistant = self.repository.get_message_at_position(
                    self.session,
                    conversation_id,
                    existing.position + 1,
                )
                if assistant is not None:
                    return MessagePair(existing, assistant)
        position = self.repository.max_position(self.session, conversation_id) + 1
        now = utc_now()
        user_message = self.repository.add_message(
            self.session,
            conversation_id,
            "user",
            content,
            position,
            client_request_id,
        )
        user_message.created_at = now
        user_message.updated_at = now
        character = self.localized_character(
            bundle.character,
            bundle.conversation.locale,
        )
        assistant_message = self.repository.add_message(
            self.session,
            conversation_id,
            "assistant",
            character["sample_reply"] or character["greeting"],
            position + 1,
        )
        assistant_message.created_at = now
        assistant_message.updated_at = now
        self.repository.touch(bundle.conversation, now)
        self.session.commit()
        return MessagePair(user_message, assistant_message)
