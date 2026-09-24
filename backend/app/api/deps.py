from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.phone import normalize_phone
from app.db.models import User
from app.db.session import get_db
from app.providers import ProviderClient, get_provider
from app.services import (
    AdminService,
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


def allowed_origins(request: Request, settings: Settings) -> set[str]:
    request_origin = str(request.base_url).rstrip("/")
    origins = set(settings.cors_origin_list)
    if settings.environment.lower() != "production":
        origins.add(request_origin)
    return origins


def require_safe_origin(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if origin and origin not in allowed_origins(request, settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The request origin is not allowed.",
        )


def require_same_origin(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if not origin or origin not in allowed_origins(request, settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The request origin is not allowed.",
        )


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


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return user


def get_god_admin(
    admin: User = Depends(get_admin_user),
    settings: Settings = Depends(get_settings),
) -> User:
    configured_phone = settings.god_user_phone.strip()
    if not configured_phone:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="God-user access is not configured.",
        )
    try:
        is_god_user = normalize_phone(configured_phone) == normalize_phone(admin.phone)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="God-user access is not configured.",
        ) from error
    if not is_god_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="God-user access is required.",
        )
    return admin


def get_admin_service(
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminService:
    return AdminService(session, settings)
