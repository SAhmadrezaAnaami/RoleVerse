from pydantic import BaseModel, ConfigDict


class CharacterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    locale: str
    name: str
    tagline: str
    description: str
    greeting: str
    avatar_url: str | None
    accent_start: str
    accent_end: str
    tags: list[str]
    category: str
    default_language: str
    is_featured: bool


class CharacterDetail(CharacterSummary):
    pass
