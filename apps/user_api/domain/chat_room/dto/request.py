from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class ChatRoomRequest(BaseModel):
    pass
