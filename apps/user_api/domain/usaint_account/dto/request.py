from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class UsaintAccountRequest(BaseModel):
    pass
