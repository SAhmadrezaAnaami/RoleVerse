from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.phone import normalize_phone


class OtpRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=32)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)


class OtpVerifyRequest(OtpRequest):
    code: str = Field(min_length=4, max_length=12, pattern=r"^\d+$")


class OtpRequestResponse(BaseModel):
    message: str
    expires_in_seconds: int
    retry_after_seconds: int


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str
    display_name: str
    role: str
    status: str
    preferred_language: str


class SessionResponse(BaseModel):
    user: UserRead
    expires_at: datetime
