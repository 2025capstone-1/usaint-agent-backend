from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class ScheduleRequest(BaseModel):
    pass
