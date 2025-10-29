from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from apps.user_api.domain.chat_room.entity import ChatRoom


class ChatRoomResponse(BaseModel):
    chat_room_id: int
    summary: str | None
    last_content: str | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(chat_room: ChatRoom) -> "ChatRoomResponse":
        return ChatRoomResponse(
            chat_room_id=chat_room.chat_room_id,
            summary=chat_room.summary,
            last_content=chat_room.last_content,
            created_at=chat_room.created_at,
            updated_at=chat_room.updated_at,
        )
