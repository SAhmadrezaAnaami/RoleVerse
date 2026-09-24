import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_current_user, get_generation_service, get_rate_limiter
from app.db.models import User
from app.providers.base import ProviderError
from app.schemas.conversations import MessagePairResponse, MessageRead
from app.schemas.generation import GenerationStatusRead
from app.services import (
    GenerationConflictError,
    GenerationInputError,
    GenerationNotFoundError,
    GenerationService,
    InMemoryRateLimiter,
)
from app.services.generation_service import GenerationContext

router = APIRouter(prefix="/conversations", tags=["generations"])


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def message_data(message) -> dict:
    return MessageRead.model_validate(message).model_dump(mode="json")


def streaming_service(service: GenerationService, bind) -> GenerationService:
    session = sessionmaker(
        bind=bind,
        autoflush=False,
        expire_on_commit=False,
    )()
    return GenerationService(session, service.provider, service.settings)


def enforce_rate_limit(
    user: User,
    service: GenerationService,
    limiter: InMemoryRateLimiter,
) -> None:
    settings = service.settings
    window = settings.generation_rate_limit_window_seconds
    user_decision = limiter.check(
        f"generation:user:{user.id}",
        settings.generation_rate_limit_per_user,
        window,
    )
    global_decision = limiter.check(
        "generation:global",
        settings.generation_rate_limit_global,
        window,
    )
    decision = user_decision if not user_decision.allowed else global_decision
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Generation rate limit reached.",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )


def generation_status(context: GenerationContext) -> GenerationStatusRead:
    return GenerationStatusRead(
        run_id=context.run.id,
        status=context.run.status,
        user_message=MessageRead.model_validate(context.user_message),
        assistant_message=(
            MessageRead.model_validate(context.assistant_message)
            if context.assistant_message is not None
            else None
        ),
    )


@router.get("/{conversation_id}/generations/{run_id}", response_model=GenerationStatusRead)
async def get_generation_status(
    conversation_id: str,
    run_id: str,
    user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
) -> GenerationStatusRead:
    try:
        context = service.load_run(conversation_id, user.id, run_id)
    except GenerationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found.") from error
    return generation_status(context)


@router.post("/{conversation_id}/generations/{run_id}/cancel", response_model=GenerationStatusRead)
async def cancel_generation(
    conversation_id: str,
    run_id: str,
    user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
) -> GenerationStatusRead:
    try:
        context = service.load_run(conversation_id, user.id, run_id)
    except GenerationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found.") from error
    if context.run.status in {"queued", "streaming"}:
        service.cancel(context, context.assistant_message.content if context.assistant_message else "")
    return generation_status(context)


@router.post("/{conversation_id}/messages/{message_id}/response")
async def generate_response(
    conversation_id: str,
    message_id: str,
    user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
    limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> MessagePairResponse:
    enforce_rate_limit(user, service, limiter)
    try:
        context = service.prepare(conversation_id, user.id, message_id)
    except GenerationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.") from error
    except GenerationInputError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except GenerationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Generation is already in progress.") from error
    if context.already_complete:
        return MessagePairResponse(
            user_message=MessageRead.model_validate(context.user_message),
            assistant_message=(
                MessageRead.model_validate(context.assistant_message)
                if context.assistant_message is not None
                else None
            ),
            mode="provider" if service.settings.live_provider_enabled else "preview",
        )
    service.start(context)
    try:
        result = await service.provider.complete(
            context.provider_messages,
            service.settings.provider_max_output_tokens,
        )
    except ProviderError as error:
        service.fail(context)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Generation service unavailable.") from error
    service.complete(
        context,
        result.content,
        result.input_tokens,
        result.output_tokens,
        result.finish_reason,
    )
    return MessagePairResponse(
        user_message=MessageRead.model_validate(context.user_message),
        assistant_message=(
            MessageRead.model_validate(context.assistant_message)
            if context.assistant_message is not None
            else None
        ),
        mode="provider" if service.settings.live_provider_enabled else "preview",
    )


@router.post("/{conversation_id}/messages/{message_id}/responses")
async def stream_response(
    conversation_id: str,
    message_id: str,
    user: User = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service),
    limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> StreamingResponse:
    enforce_rate_limit(user, service, limiter)
    try:
        context = service.prepare(conversation_id, user.id, message_id)
    except GenerationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.") from error
    except GenerationInputError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except GenerationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Generation is already in progress.") from error

    if context.already_complete:
        async def replay_completed() -> AsyncIterator[str]:
            yield sse_event(
                "done",
                {
                    "sequence": 1,
                    "user_message": message_data(context.user_message),
                    "assistant_message": message_data(context.assistant_message) if context.assistant_message else None,
                    "mode": "preview",
                },
            )

        return StreamingResponse(
            replay_completed(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    service.start(context)
    stream_bind = service.session.get_bind()
    settings = service.settings
    mode = "provider" if settings.live_provider_enabled else "preview"

    async def event_stream() -> AsyncIterator[str]:
        sequence = 0
        partial_content = []
        input_tokens = None
        output_tokens = None
        finish_reason = None
        stream_service = streaming_service(service, stream_bind)
        stream_context = None

        def next_event(event_name: str, payload: dict) -> str:
            nonlocal sequence
            sequence += 1
            return sse_event(event_name, {"sequence": sequence, **payload})

        try:
            stream_context = stream_service.load_existing(
                conversation_id,
                user.id,
                message_id,
            )
            yield next_event(
                "start",
                {
                    "run_id": stream_context.run.id,
                    "user_message": message_data(stream_context.user_message),
                    "assistant_message_id": stream_context.assistant_message.id if stream_context.assistant_message else None,
                },
            )
            async for chunk in stream_service.provider.stream(
                stream_context.provider_messages,
                settings.provider_max_output_tokens,
            ):
                if chunk.delta:
                    partial_content.append(chunk.delta)
                    yield next_event(
                        "delta",
                        {
                            "run_id": stream_context.run.id,
                            "text": chunk.delta,
                        },
                    )
                if chunk.input_tokens is not None:
                    input_tokens = chunk.input_tokens
                if chunk.output_tokens is not None:
                    output_tokens = chunk.output_tokens
                if chunk.finish_reason is not None:
                    finish_reason = chunk.finish_reason
            content = "".join(partial_content)
            stream_service.complete(
                stream_context,
                content,
                input_tokens,
                output_tokens,
                finish_reason,
            )
            yield next_event(
                "done",
                {
                    "run_id": stream_context.run.id,
                    "user_message": message_data(stream_context.user_message),
                    "assistant_message": message_data(stream_context.assistant_message) if stream_context.assistant_message else None,
                    "mode": mode,
                },
            )
        except asyncio.CancelledError:
            if stream_context is not None:
                stream_service.cancel(stream_context, "".join(partial_content))
            raise
        except ProviderError:
            if stream_context is not None:
                stream_service.fail(stream_context, "".join(partial_content))
            yield next_event(
                "error",
                {
                    "run_id": context.run.id,
                    "code": "provider_unavailable",
                    "message": "Generation is temporarily unavailable.",
                },
            )
        finally:
            stream_service.session.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
