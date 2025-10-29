from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


class CreateChatRoomRequest(BaseModel):
    summary: str | None = None
