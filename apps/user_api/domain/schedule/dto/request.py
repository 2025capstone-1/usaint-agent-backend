from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel,Field

class ScheduleRequest(BaseModel):
    pass

class CreateScheduleRequest(ScheduleRequest):
    cron: str = Field(..., description="Cron expression for the schedule")
    content: str = Field(..., description="Content to be scheduled")