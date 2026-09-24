from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_character_service
from app.schemas.characters import CharacterDetail, CharacterSummary
from app.services import CharacterNotFoundError, CharacterService

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("", response_model=list[CharacterSummary])
async def list_characters(
    search: str | None = Query(default=None, max_length=80),
    category: str | None = Query(default=None, max_length=40),
    locale: str = Query(default="en", pattern="^(en|fa)$"),
    limit: int = Query(default=24, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    service: CharacterService = Depends(get_character_service),
) -> list[CharacterSummary]:
    characters = service.list_characters(search, category, limit, offset, locale)
    return [CharacterSummary.model_validate(character) for character in characters]


@router.get("/{slug}", response_model=CharacterDetail)
async def get_character(
    slug: str,
    locale: str = Query(default="en", pattern="^(en|fa)$"),
    service: CharacterService = Depends(get_character_service),
) -> CharacterDetail:
    try:
        character = service.get_character(slug, locale)
    except CharacterNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found.") from error
    return CharacterDetail.model_validate(character)
