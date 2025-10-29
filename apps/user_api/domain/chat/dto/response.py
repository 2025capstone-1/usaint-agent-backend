from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel
from apps.user_api.domain.chat.entity import Chat


class ChatResponse(BaseModel):
    chat_id: int
    content: str
    sender: str
    type: str | None
    created_at: datetime

    @staticmethod
    def from_entity(chat: Chat) -> "ChatResponse":
        return ChatResponse(
            chat_id=chat.chat_id,
            content=chat.content,
            sender=chat.sender,
            type=chat.type,
            created_at=chat.created_at,
        )
