from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.db.models import (
    AuditEvent,
    Conversation,
    GenerationRun,
    Message,
    ProviderConnection,
    ProviderModel,
    SystemSetting,
    User,
)


class AdminRepository:
    def list_users(
        self,
        session: Session,
        search: str = "",
        role: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        statement = select(User)
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(User.phone.ilike(pattern), User.display_name.ilike(pattern))
            )
        if role:
            statement = statement.where(User.role == role)
        if status:
            statement = statement.where(User.status == status)
        statement = statement.order_by(User.created_at.desc()).offset(offset).limit(limit)
        return list(session.scalars(statement))

    def count_users(
        self,
        session: Session,
        search: str = "",
        role: str | None = None,
        status: str | None = None,
    ) -> int:
        statement = select(func.count(User.id))
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(User.phone.ilike(pattern), User.display_name.ilike(pattern))
            )
        if role:
            statement = statement.where(User.role == role)
        if status:
            statement = statement.where(User.status == status)
        return session.scalar(statement) or 0

    def get_user(self, session: Session, user_id: str) -> User | None:
        return session.get(User, user_id)

    def count_active_admins(self, session: Session) -> int:
        statement = select(func.count(User.id)).where(
            User.role == "admin",
            User.status == "active",
        )
        return session.scalar(statement) or 0

    def cancel_active_generations_for_user(
        self,
        session: Session,
        user_id: str,
        cancelled_at: datetime,
    ) -> int:
        statement = (
            select(GenerationRun)
            .join(Conversation, GenerationRun.conversation_id == Conversation.id)
            .where(
                Conversation.user_id == user_id,
                GenerationRun.status.in_(("queued", "streaming")),
            )
        )
        runs = list(session.scalars(statement))
        cancelled_count = 0
        for run in runs:
            result = session.execute(
                update(GenerationRun)
                .where(
                    GenerationRun.id == run.id,
                    GenerationRun.status.in_(("queued", "streaming")),
                )
                .values(
                    status="cancelled",
                    completed_at=cancelled_at,
                    updated_at=cancelled_at,
                )
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                continue
            cancelled_count += 1
            if run.assistant_message_id:
                assistant = session.get(Message, run.assistant_message_id)
                if assistant is not None:
                    assistant.status = "cancelled"
                    assistant.updated_at = cancelled_at
        return cancelled_count

    def list_provider_connections(self, session: Session) -> list[ProviderConnection]:
        statement = select(ProviderConnection).order_by(
            ProviderConnection.is_default.desc(),
            ProviderConnection.name.asc(),
        )
        return list(session.scalars(statement))

    def get_provider_connection(
        self,
        session: Session,
        provider_id: str,
    ) -> ProviderConnection | None:
        return session.get(ProviderConnection, provider_id)

    def create_provider_connection(
        self,
        session: Session,
        name: str,
        slug: str,
        adapter: str,
        base_url: str,
        status: str,
        is_default: bool,
        secret_source: str,
        actor_id: str,
    ) -> ProviderConnection:
        provider = ProviderConnection(
            name=name,
            slug=slug,
            adapter=adapter,
            base_url=base_url,
            status=status,
            is_default=is_default,
            secret_source=secret_source,
            created_by=actor_id,
        )
        session.add(provider)
        session.flush()
        return provider

    def update_provider_connection(
        self,
        provider: ProviderConnection,
        values: dict[str, Any],
    ) -> None:
        for key, value in values.items():
            setattr(provider, key, value)

    def list_provider_models(
        self,
        session: Session,
        provider_id: str,
    ) -> list[ProviderModel]:
        statement = select(ProviderModel).where(
            ProviderModel.provider_id == provider_id,
        ).order_by(ProviderModel.name.asc())
        return list(session.scalars(statement))

    def get_provider_model_by_name(
        self,
        session: Session,
        provider_id: str,
        name: str,
    ) -> ProviderModel | None:
        statement = select(ProviderModel).where(
            ProviderModel.provider_id == provider_id,
            ProviderModel.name == name,
        )
        return session.scalar(statement)

    def get_provider_model(
        self,
        session: Session,
        provider_id: str,
        model_id: str,
    ) -> ProviderModel | None:
        statement = select(ProviderModel).where(
            ProviderModel.id == model_id,
            ProviderModel.provider_id == provider_id,
        )
        return session.scalar(statement)

    def create_provider_model(
        self,
        session: Session,
        provider_id: str,
        values: dict[str, Any],
    ) -> ProviderModel:
        model = ProviderModel(provider_id=provider_id, **values)
        session.add(model)
        session.flush()
        return model

    def update_provider_model(
        self,
        model: ProviderModel,
        values: dict[str, Any],
    ) -> None:
        for key, value in values.items():
            setattr(model, key, value)

    def list_settings(self, session: Session) -> list[SystemSetting]:
        statement = select(SystemSetting).order_by(SystemSetting.key.asc())
        return list(session.scalars(statement))

    def get_setting(self, session: Session, key: str) -> SystemSetting | None:
        statement = select(SystemSetting).where(SystemSetting.key == key)
        return session.scalar(statement)

    def upsert_setting(
        self,
        session: Session,
        key: str,
        value: Any,
        actor_id: str,
    ) -> SystemSetting:
        setting = self.get_setting(session, key)
        if setting is None:
            setting = SystemSetting(key=key, value=value, updated_by=actor_id)
            session.add(setting)
        else:
            setting.value = value
            setting.updated_by = actor_id
        session.flush()
        return setting

    def create_audit_event(
        self,
        session: Session,
        actor_id: str | None,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any],
        created_at: datetime,
    ) -> AuditEvent:
        event = AuditEvent(
            actor_user_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            created_at=created_at,
        )
        session.add(event)
        session.flush()
        return event

    def list_audit_events(
        self,
        session: Session,
        limit: int = 50,
    ) -> list[AuditEvent]:
        statement = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
        return list(session.scalars(statement))

    def overview_metrics(self, session: Session) -> dict[str, int]:
        user_status_rows = session.execute(
            select(User.status, func.count(User.id)).group_by(User.status)
        ).all()
        user_counts = {status: count for status, count in user_status_rows}
        generation_status_rows = session.execute(
            select(GenerationRun.status, func.count(GenerationRun.id)).group_by(GenerationRun.status)
        ).all()
        generation_counts = {status: count for status, count in generation_status_rows}
        usage = session.execute(
            select(
                func.coalesce(func.sum(GenerationRun.input_tokens), 0),
                func.coalesce(func.sum(GenerationRun.output_tokens), 0),
                func.coalesce(func.sum(GenerationRun.total_cost_micro), 0),
            )
        ).one()
        usage_reported = session.scalar(
            select(func.count(GenerationRun.id)).where(GenerationRun.usage_available.is_(True))
        ) or 0
        pricing_reported = session.scalar(
            select(func.count(GenerationRun.id)).where(GenerationRun.pricing_available.is_(True))
        ) or 0
        return {
            "users_total": sum(user_counts.values()),
            "users_active": user_counts.get("active", 0),
            "users_banned": user_counts.get("banned", 0),
            "conversations_total": session.scalar(select(func.count(Conversation.id))) or 0,
            "generations_total": sum(generation_counts.values()),
            "generations_complete": generation_counts.get("complete", 0),
            "generations_active": generation_counts.get("queued", 0) + generation_counts.get("streaming", 0),
            "input_tokens": int(usage[0] or 0),
            "output_tokens": int(usage[1] or 0),
            "total_cost_micro": int(usage[2] or 0),
            "usage_reported": int(usage_reported),
            "pricing_reported": int(pricing_reported),
            "providers_total": session.scalar(select(func.count(ProviderConnection.id))) or 0,
        }

    def list_usage_runs(
        self,
        session: Session,
        limit: int = 50,
        start: datetime | None = None,
        end: datetime | None = None,
        user_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> list[tuple[GenerationRun, str]]:
        statement = (
            select(GenerationRun, Conversation.user_id)
            .join(Conversation, GenerationRun.conversation_id == Conversation.id)
        )
        if start is not None:
            statement = statement.where(GenerationRun.created_at >= start)
        if end is not None:
            statement = statement.where(GenerationRun.created_at < end)
        if user_id:
            statement = statement.where(Conversation.user_id == user_id)
        if provider:
            statement = statement.where(GenerationRun.provider_name == provider)
        if model:
            statement = statement.where(GenerationRun.model_name == model)
        statement = statement.order_by(GenerationRun.created_at.desc()).limit(limit)
        return list(session.execute(statement).all())
