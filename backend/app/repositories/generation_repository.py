from datetime import datetime

from sqlalchemy import select, update
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

    def mark_streaming(
        self,
        session: Session,
        run: GenerationRun,
        updated_at: datetime,
    ) -> bool:
        statement = (
            update(GenerationRun)
            .where(
                GenerationRun.id == run.id,
                GenerationRun.status == "queued",
            )
            .values(status="streaming", updated_at=updated_at)
            .execution_options(synchronize_session=False)
        )
        updated = session.execute(statement).rowcount == 1
        if updated:
            run.status = "streaming"
            run.updated_at = updated_at
        return updated

    def complete(
        self,
        session: Session,
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
    ) -> bool:
        statement = (
            update(GenerationRun)
            .where(
                GenerationRun.id == run.id,
                GenerationRun.status.in_(("queued", "streaming")),
            )
            .values(
                status="complete",
                usage_available=usage_available,
                pricing_available=pricing_available,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=finish_reason,
                input_cost_micro=input_cost_micro,
                output_cost_micro=output_cost_micro,
                total_cost_micro=total_cost_micro,
                completed_at=completed_at,
                updated_at=completed_at,
            )
            .execution_options(synchronize_session=False)
        )
        updated = session.execute(statement).rowcount == 1
        if updated:
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
            run.updated_at = completed_at
        return updated

    def fail(
        self,
        session: Session,
        run: GenerationRun,
        error_code: str,
        completed_at: datetime,
    ) -> bool:
        statement = (
            update(GenerationRun)
            .where(
                GenerationRun.id == run.id,
                GenerationRun.status.in_(("queued", "streaming")),
            )
            .values(
                status="failed",
                error_code=error_code,
                completed_at=completed_at,
                updated_at=completed_at,
            )
            .execution_options(synchronize_session=False)
        )
        updated = session.execute(statement).rowcount == 1
        if updated:
            run.status = "failed"
            run.error_code = error_code
            run.completed_at = completed_at
            run.updated_at = completed_at
        return updated

    def cancel(
        self,
        session: Session,
        run: GenerationRun,
        completed_at: datetime,
    ) -> bool:
        statement = (
            update(GenerationRun)
            .where(
                GenerationRun.id == run.id,
                GenerationRun.status.in_(("queued", "streaming")),
            )
            .values(
                status="cancelled",
                completed_at=completed_at,
                updated_at=completed_at,
            )
            .execution_options(synchronize_session=False)
        )
        updated = session.execute(statement).rowcount == 1
        if updated:
            run.status = "cancelled"
            run.completed_at = completed_at
            run.updated_at = completed_at
        return updated
