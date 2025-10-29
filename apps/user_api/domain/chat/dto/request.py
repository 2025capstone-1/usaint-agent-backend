from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

class CreateChatRequest(BaseModel):
    content: str