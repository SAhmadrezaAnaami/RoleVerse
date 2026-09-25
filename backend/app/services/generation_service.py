from dataclasses import dataclass

from app.core.config import Settings
from app.db.base import utc_now
from app.db.models import Character, Conversation, GenerationRun, Message
from app.providers.base import ProviderClient, ProviderMessage
from app.repositories import ConversationRepository, GenerationRepository
from app.services.conversation_service import ConversationService
from app.services.prompt_service import build_provider_messages


class GenerationNotFoundError(Exception):
    pass


class GenerationConflictError(Exception):
    pass


class GenerationInputError(Exception):
    pass


@dataclass
class GenerationContext:
    conversation: Conversation
    character: Character
    user_message: Message
    assistant_message: Message | None
    run: GenerationRun
    provider_messages: list[ProviderMessage]
    already_complete: bool = False


class GenerationService:
    def __init__(
        self,
        session,
        provider: ProviderClient,
        settings: Settings,
        clock=utc_now,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings
        self.clock = clock
        self.conversation_repository = ConversationRepository()
        self.generation_repository = GenerationRepository()
        self.conversation_service = ConversationService(session)

    def prepare(
        self,
        conversation_id: str,
        user_id: str,
        user_message_id: str,
    ) -> GenerationContext:
        bundle = self.conversation_service.get_for_user(conversation_id, user_id)
        user_message = self.conversation_repository.get_message_for_conversation(
            self.session,
            conversation_id,
            user_message_id,
        )
        if user_message is None or user_message.role != "user" or user_message.status != "complete":
            raise GenerationNotFoundError("User message not found.")
        if self.settings.live_provider_enabled and not user_message.client_request_id:
            raise GenerationInputError("A client request identifier is required for live generation.")
        existing = self.generation_repository.get_by_user_message(
            self.session,
            user_message_id,
        )
        if existing is not None:
            if existing.status == "complete":
                assistant = self.conversation_repository.get_message_by_id(
                    self.session,
                    existing.assistant_message_id or "",
                )
                return GenerationContext(
                    conversation=bundle.conversation,
                    character=bundle.character,
                    user_message=user_message,
                    assistant_message=assistant,
                    run=existing,
                    provider_messages=[],
                    already_complete=True,
                )
            raise GenerationConflictError("Generation is already in progress.")
        history = self.conversation_repository.list_messages(
            self.session,
            conversation_id,
            200,
        )
        now = self.clock()
        position = self.conversation_repository.max_position(self.session, conversation_id) + 1
        assistant = self.conversation_repository.add_message(
            self.session,
            conversation_id,
            "assistant",
            "",
            position,
            source="generation",
        )
        assistant.status = "queued"
        assistant.created_at = now
        assistant.updated_at = now
        run = self.generation_repository.create(
            self.session,
            conversation_id,
            user_message.id,
            assistant.id,
            self.provider.name,
            self.provider.model,
            now,
        )
        self.conversation_repository.touch(bundle.conversation, now)
        self.session.commit()
        provider_messages = build_provider_messages(
            bundle.character,
            history,
            user_message,
            bundle.conversation.locale,
        )
        return GenerationContext(
            conversation=bundle.conversation,
            character=bundle.character,
            user_message=user_message,
            assistant_message=assistant,
            run=run,
            provider_messages=provider_messages,
        )

    def load_existing(
        self,
        conversation_id: str,
        user_id: str,
        user_message_id: str,
    ) -> GenerationContext:
        bundle = self.conversation_service.get_for_user(conversation_id, user_id)
        user_message = self.conversation_repository.get_message_for_conversation(
            self.session,
            conversation_id,
            user_message_id,
        )
        if user_message is None or user_message.role != "user" or user_message.status != "complete":
            raise GenerationNotFoundError("User message not found.")
        run = self.generation_repository.get_by_user_message(
            self.session,
            user_message_id,
        )
        if run is None:
            raise GenerationNotFoundError("Generation not found.")
        assistant = self.conversation_repository.get_message_by_id(
            self.session,
            run.assistant_message_id or "",
        )
        history = self.conversation_repository.list_messages(
            self.session,
            conversation_id,
            200,
        )
        return GenerationContext(
            conversation=bundle.conversation,
            character=bundle.character,
            user_message=user_message,
            assistant_message=assistant,
            run=run,
            provider_messages=build_provider_messages(
                bundle.character,
                history,
                user_message,
                bundle.conversation.locale,
            ),
            already_complete=run.status == "complete",
        )

    def load_run(
        self,
        conversation_id: str,
        user_id: str,
        run_id: str,
    ) -> GenerationContext:
        bundle = self.conversation_service.get_for_user(conversation_id, user_id)
        run = self.generation_repository.get_by_id_for_conversation(
            self.session,
            conversation_id,
            run_id,
        )
        if run is None:
            raise GenerationNotFoundError("Generation not found.")
        user_message = self.conversation_repository.get_message_by_id(
            self.session,
            run.user_message_id,
        )
        if user_message is None or user_message.conversation_id != conversation_id:
            raise GenerationNotFoundError("Generation not found.")
        assistant = self.conversation_repository.get_message_by_id(
            self.session,
            run.assistant_message_id or "",
        )
        history = self.conversation_repository.list_messages(
            self.session,
            conversation_id,
            200,
        )
        return GenerationContext(
            conversation=bundle.conversation,
            character=bundle.character,
            user_message=user_message,
            assistant_message=assistant,
            run=run,
            provider_messages=build_provider_messages(
                bundle.character,
                history,
                user_message,
                bundle.conversation.locale,
            ),
            already_complete=run.status == "complete",
        )

    def start(self, context: GenerationContext) -> bool:
        if context.already_complete:
            return False
        now = self.clock()
        if not self.generation_repository.mark_streaming(self.session, context.run, now):
            self.session.rollback()
            return False
        if context.assistant_message is not None:
            context.assistant_message.status = "streaming"
            context.assistant_message.updated_at = now
        context.run.updated_at = now
        self.session.commit()
        return True

    def complete(
        self,
        context: GenerationContext,
        content: str,
        input_tokens: int | None,
        output_tokens: int | None,
        finish_reason: str | None = None,
    ) -> bool:
        if context.already_complete or context.run.status in {"complete", "failed", "cancelled"}:
            return False
        now = self.clock()
        usage_available = (
            input_tokens is not None
            and output_tokens is not None
            and input_tokens >= 0
            and output_tokens >= 0
        )
        pricing_available = (
            self.settings.provider_input_price_micro_per_million > 0
            or self.settings.provider_output_price_micro_per_million > 0
        )
        safe_input_tokens = input_tokens if usage_available and input_tokens is not None else 0
        safe_output_tokens = output_tokens if usage_available and output_tokens is not None else 0
        input_cost = self.calculate_cost(
            safe_input_tokens,
            self.settings.provider_input_price_micro_per_million,
        ) if usage_available else 0
        output_cost = self.calculate_cost(
            safe_output_tokens,
            self.settings.provider_output_price_micro_per_million,
        ) if usage_available else 0
        updated = self.generation_repository.complete(
            self.session,
            context.run,
            safe_input_tokens,
            safe_output_tokens,
            finish_reason,
            usage_available,
            pricing_available,
            input_cost,
            output_cost,
            input_cost + output_cost,
            now,
        )
        if not updated:
            self.session.rollback()
            return False
        if context.assistant_message is not None:
            context.assistant_message.content = content
            context.assistant_message.status = "complete"
            context.assistant_message.updated_at = now
        self.conversation_repository.touch(context.conversation, now)
        self.session.commit()
        return True

    def fail(self, context: GenerationContext, partial_content: str = "") -> bool:
        if context.already_complete or context.run.status in {"complete", "failed", "cancelled"}:
            return False
        now = self.clock()
        updated = self.generation_repository.fail(
            self.session,
            context.run,
            "provider_unavailable",
            now,
        )
        if not updated:
            self.session.rollback()
            return False
        if context.assistant_message is not None:
            context.assistant_message.content = partial_content
            context.assistant_message.status = "failed"
            context.assistant_message.updated_at = now
        self.session.commit()
        return True

    def cancel(self, context: GenerationContext, partial_content: str = "") -> bool:
        if context.already_complete or context.run.status in {"complete", "failed", "cancelled"}:
            return False
        now = self.clock()
        updated = self.generation_repository.cancel(
            self.session,
            context.run,
            now,
        )
        if not updated:
            self.session.rollback()
            return False
        if context.assistant_message is not None:
            context.assistant_message.content = partial_content
            context.assistant_message.status = "cancelled"
            context.assistant_message.updated_at = now
        self.session.commit()
        return True

    @staticmethod
    def calculate_cost(tokens: int, price_per_million: int) -> int:
        return (max(0, tokens) * max(0, price_per_million) + 500_000) // 1_000_000
