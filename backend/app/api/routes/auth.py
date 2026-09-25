from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_current_user, get_otp_service, require_csrf, require_safe_origin
from app.core.config import Settings, get_settings
from app.db.models import User
from app.schemas.auth import OtpRequest, OtpRequestResponse, OtpVerifyRequest, SessionResponse, UserRead
from app.services import AccountBlockedError, InvalidOtpError, OtpCooldownError, OtpService

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(require_safe_origin)],
)


@router.post("/otp/request", response_model=OtpRequestResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_otp(
    payload: OtpRequest,
    request: Request,
    service: OtpService = Depends(get_otp_service),
    settings: Settings = Depends(get_settings),
) -> OtpRequestResponse:
    request_ip = request.client.host if request.client else None
    try:
        expires_at, retry_after = service.request_otp(payload.phone, request_ip)
    except OtpCooldownError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A verification code was requested recently.",
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    return OtpRequestResponse(
        message="A development verification code was generated in the server console.",
        expires_in_seconds=settings.otp_ttl_minutes * 60,
        retry_after_seconds=retry_after,
    )


@router.post("/otp/verify", response_model=SessionResponse)
async def verify_otp(
    payload: OtpVerifyRequest,
    request: Request,
    response: Response,
    service: OtpService = Depends(get_otp_service),
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    if settings.environment in {"staging", "production"} and request.url.scheme != "https":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication requires HTTPS.",
        )
    try:
        issued_session = service.verify_otp(
            payload.phone,
            payload.code,
            request.headers.get("user-agent"),
        )
    except AccountBlockedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except InvalidOtpError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    response.set_cookie(
        key=settings.session_cookie_name,
        value=issued_session.token,
        max_age=settings.session_ttl_minutes * 60,
        expires=issued_session.expires_at,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.set_cookie(
        key="roleverse_csrf",
        value=issued_session.csrf_token,
        max_age=settings.session_ttl_minutes * 60,
        expires=issued_session.expires_at,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return SessionResponse(
        user=UserRead.model_validate(issued_session.user),
        expires_at=issued_session.expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: OtpService = Depends(get_otp_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    service.logout(request.cookies.get(settings.session_cookie_name, ""))
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key="roleverse_csrf",
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def logout_all(
    response: Response,
    user: User = Depends(get_current_user),
    service: OtpService = Depends(get_otp_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    service.logout_all(user.id)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key="roleverse_csrf",
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)
