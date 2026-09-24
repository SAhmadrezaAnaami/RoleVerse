from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.providers.base import ProviderError
from app.services.rate_limit import InMemoryRateLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A bilingual role-play chat platform.",
        docs_url=None if settings.environment.lower() == "production" else "/docs",
        redoc_url=None if settings.environment.lower() == "production" else "/redoc",
        openapi_url=None if settings.environment.lower() == "production" else "/openapi.json",
    )
    application.state.settings = settings
    application.state.rate_limiter = InMemoryRateLimiter()

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, error: RequestValidationError) -> JSONResponse:
        details = [
            {
                "loc": list(item["loc"]),
                "msg": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ]
        headers = {}
        if (
            request.url.path.startswith(f"{settings.api_prefix}/auth")
            or request.url.path.startswith(f"{settings.api_prefix}/conversations")
            or request.url.path.startswith(f"{settings.api_prefix}/admin")
        ):
            headers = {"Cache-Control": "no-store", "Pragma": "no-cache"}
        return JSONResponse(status_code=422, content={"detail": details}, headers=headers)

    @application.exception_handler(ProviderError)
    async def provider_exception_handler(request: Request, error: ProviderError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Generation service unavailable."},
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )

    @application.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if (
            request.url.path.startswith(f"{settings.api_prefix}/auth")
            or request.url.path.startswith(f"{settings.api_prefix}/conversations")
            or request.url.path.startswith(f"{settings.api_prefix}/admin")
            or request.url.path.startswith("/admin")
        ):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        if request.url.path.startswith("/admin"):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            )
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    application.include_router(api_router, prefix=settings.api_prefix)

    client_directory = settings.client_directory
    if client_directory.exists():
        application.mount(
            "/",
            StaticFiles(directory=client_directory, html=True),
            name="client",
        )
    return application


app = create_app()
