from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.characters import router as characters_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.generations import router as generations_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(characters_router)
api_router.include_router(conversations_router)
api_router.include_router(generations_router)
