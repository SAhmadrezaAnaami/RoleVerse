from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_db
from app.providers import ProviderClient, get_provider
from app.services import (
    CharacterService,
    ConversationService,
    GenerationService,
    InMemoryRateLimiter,
    OtpService,
)


def get_otp_service(
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OtpService:
    return OtpService(session, settings)


def get_character_service(session: Session = Depends(get_db)) -> CharacterService:
    return CharacterService(session)


def get_conversation_service(session: Session = Depends(get_db)) -> ConversationService:
    return ConversationService(session)


def get_provider_client(settings: Settings = Depends(get_settings)) -> ProviderClient:
    return get_provider(settings)


def get_generation_service(
    session: Session = Depends(get_db),
    provider: ProviderClient = Depends(get_provider_client),
    settings: Settings = Depends(get_settings),
) -> GenerationService:
    return GenerationService(session, provider, settings)


def get_rate_limiter(request: Request) -> InMemoryRateLimiter:
    return request.app.state.rate_limiter


def get_current_user(
    request: Request,
    service: OtpService = Depends(get_otp_service),
) -> User:
    token = request.cookies.get(service.settings.session_cookie_name)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Session"},
        )
    user = service.user_from_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Session"},
        )
    return user
