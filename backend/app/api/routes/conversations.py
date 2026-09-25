from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_conversation_service,
    get_current_user,
    require_csrf,
    require_safe_origin,
)
from app.db.models import User
from app.schemas.characters import CharacterSummary
from app.schemas.conversations import (
    ConversationCreateRequest,
    ConversationRead,
    MessageCreateRequest,
    MessagePairResponse,
    MessageRead,
)
from app.services import (
    CharacterNotFoundError,
    ConversationInactiveError,
    ConversationNotFoundError,
    ConversationService,
    IdempotencyConflictError,
)

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(require_safe_origin), Depends(require_csrf)],
)


def to_conversation_read(bundle, service: ConversationService) -> ConversationRead:
    character = service.localized_character(
        bundle.character,
        bundle.conversation.locale,
    )
    summary = service.summary_fields(bundle)
    return ConversationRead(
        id=bundle.conversation.id,
        title=bundle.conversation.title,
        locale=bundle.conversation.locale,
        status=bundle.conversation.status,
        created_at=bundle.conversation.created_at,
        updated_at=bundle.conversation.updated_at,
        last_message_at=bundle.conversation.last_message_at,
        last_message_preview=summary["last_message_preview"],
        message_count=summary["message_count"],
        character=CharacterSummary.model_validate(character),
    )


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationRead]:
    return [
        to_conversation_read(bundle, service)
        for bundle in service.list_for_user(user.id)
    ]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationRead:
    try:
        bundle = service.create(
            user.id,
            payload.character_slug,
            payload.title,
            payload.locale,
        )
    except CharacterNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found.") from error
    return to_conversation_read(bundle, service)


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationRead:
    try:
        bundle = service.get_for_user(conversation_id, user.id)
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.") from error
    return to_conversation_read(bundle, service)


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conversation_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> list[MessageRead]:
    try:
        messages = service.list_messages(conversation_id, user.id, limit)
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.") from error
    return [MessageRead.model_validate(message) for message in messages]


@router.post("/{conversation_id}/messages", response_model=MessagePairResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> MessagePairResponse:
    try:
        pair = service.append_message(
            conversation_id,
            user.id,
            payload.content,
            payload.client_request_id,
            include_preview=payload.mode == "preview",
        )
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.") from error
    except ConversationInactiveError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversation is not active.") from error
    except IdempotencyConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return MessagePairResponse(
        user_message=MessageRead.model_validate(pair.user_message),
        assistant_message=(
            MessageRead.model_validate(pair.assistant_message)
            if pair.assistant_message is not None
            else None
        ),
        mode=payload.mode,
    )
