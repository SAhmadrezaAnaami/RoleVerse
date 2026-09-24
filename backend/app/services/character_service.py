from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Character
from app.repositories import CharacterRepository


class CharacterNotFoundError(Exception):
    pass


class CharacterService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = CharacterRepository()

    @staticmethod
    def localized_values(character: Character, locale: str) -> dict[str, Any]:
        translations = character.translations or {}
        selected = translations.get(locale, {})
        return {
            "id": character.id,
            "slug": character.slug,
            "locale": locale,
            "name": selected.get("name", character.name),
            "tagline": selected.get("tagline", character.tagline),
            "description": selected.get("description", character.description),
            "persona": selected.get("persona", character.persona),
            "soul": selected.get("soul", character.soul),
            "backstory": selected.get("backstory", character.backstory),
            "greeting": selected.get("greeting", character.greeting),
            "sample_reply": selected.get("sample_reply", character.sample_reply),
            "avatar_url": character.avatar_url,
            "accent_start": character.accent_start,
            "accent_end": character.accent_end,
            "tags": selected.get("tags", character.tags),
            "category": character.category,
            "default_language": character.default_language,
            "is_featured": character.is_featured,
        }

    def list_characters(
        self,
        search: str | None,
        category: str | None,
        limit: int,
        offset: int,
        locale: str,
    ) -> list[dict[str, Any]]:
        characters = self.repository.list_published(
            self.session,
            search,
            category,
            limit,
            offset,
        )
        return [self.localized_values(character, locale) for character in characters]

    def get_character_model(self, slug: str) -> Character:
        character = self.repository.get_published_by_slug(self.session, slug)
        if character is None:
            raise CharacterNotFoundError("Character not found.")
        return character

    def get_character(self, slug: str, locale: str) -> dict[str, Any]:
        return self.localized_values(self.get_character_model(slug), locale)
