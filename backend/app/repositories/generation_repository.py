from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import GenerationRun


class GenerationRepository:
    def get_by_user_message(
        self,
        session: Session,
        user_message_id: str,
    ) -> GenerationRun | None:
        statement = select(GenerationRun).where(
            GenerationRun.user_message_id == user_message_id,
        )
        return session.scalar(statement)

    def get_by_id_for_conversation(
        self,
        session: Session,
        conversation_id: str,
        run_id: str,
    ) -> GenerationRun | None:
        statement = select(GenerationRun).where(
            GenerationRun.id == run_id,
            GenerationRun.conversation_id == conversation_id,
        )
        return session.scalar(statement)

    def create(
        self,
        session: Session,
        conversation_id: str,
        user_message_id: str,
        assistant_message_id: str,
        provider_name: str,
        model_name: str,
        started_at: datetime,
    ) -> GenerationRun:
        run = GenerationRun(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            provider_name=provider_name,
            model_name=model_name,
            status="queued",
            started_at=started_at,
        )
        session.add(run)
        session.flush()
        return run

    def mark_streaming(self, run: GenerationRun) -> None:
        run.status = "streaming"

    def complete(
        self,
        run: GenerationRun,
        input_tokens: int,
        output_tokens: int,
        finish_reason: str | None,
        usage_available: bool,
        pricing_available: bool,
        input_cost_micro: int,
        output_cost_micro: int,
        total_cost_micro: int,
        completed_at: datetime,
    ) -> None:
        run.status = "complete"
        run.usage_available = usage_available
        run.pricing_available = pricing_available
        run.input_tokens = input_tokens
        run.output_tokens = output_tokens
        run.finish_reason = finish_reason
        run.input_cost_micro = input_cost_micro
        run.output_cost_micro = output_cost_micro
        run.total_cost_micro = total_cost_micro
        run.completed_at = completed_at

    def fail(
        self,
        run: GenerationRun,
        error_code: str,
        completed_at: datetime,
    ) -> None:
        run.status = "failed"
        run.error_code = error_code
        run.completed_at = completed_at

    def cancel(self, run: GenerationRun, completed_at: datetime) -> None:
        run.status = "cancelled"
        run.completed_at = completed_at
