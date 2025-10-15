from __future__ import annotations

#from dataclasses import dataclass

from pydantic import BaseModel,Field
from typing import Optional

class ScheduleRequest(BaseModel):
    pass

class CreateScheduleRequest(ScheduleRequest):
    cron: str = Field(..., description="Cron expression for the schedule")
    content: str = Field(..., description="Content to be scheduled")

class UpdateScheduleRequest(ScheduleRequest):
    cron: Optional[str] = Field(None, description="Updated cron expression for the schedule")
    content: Optional[str] = Field(None, description="Updated content to be scheduled")