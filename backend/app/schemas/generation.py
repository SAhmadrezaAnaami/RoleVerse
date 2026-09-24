from typing import Literal

from pydantic import BaseModel

from app.schemas.conversations import MessageRead


class GenerationStatusRead(BaseModel):
    run_id: str
    status: Literal["queued", "streaming", "complete", "failed", "cancelled"]
    user_message: MessageRead
    assistant_message: MessageRead | None
