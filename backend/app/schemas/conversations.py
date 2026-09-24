from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.characters import CharacterSummary


class ConversationCreateRequest(BaseModel):
    character_slug: str = Field(min_length=1, max_length=80)
    title: str | None = Field(default=None, max_length=120)
    locale: Literal["en", "fa"] = "en"


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    locale: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    last_message_preview: str
    message_count: int
    character: CharacterSummary


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    status: str
    position: int
    created_at: datetime


class MessageCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(min_length=1, max_length=4000)
    client_request_id: str | None = Field(default=None, max_length=64, alias="clientRequestId")
    mode: Literal["preview", "persist"] = "preview"

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            raise ValueError("Message content cannot be empty.")
        if any(ord(character) < 32 and character not in "\n\t" for character in normalized):
            raise ValueError("Message content contains an unsupported control character.")
        return normalized


class MessagePairResponse(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead | None
    mode: Literal["preview", "persist", "provider"] = "preview"
