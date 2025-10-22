from __future__ import annotations
from datetime import datetime
from typing import List

from pydantic import BaseModel

from apps.user_api.domain.schedule.entity import Schedule


class ScheduleResponse(BaseModel):
    id: int
    cron: str
    content: str
    user_id: int
    updated_at: datetime
    created_at: datetime

    @classmethod
    def of(cls, schedule: Schedule):
        return cls(
            id=schedule.schedule_id,
            cron=schedule.cron,
            content=schedule.content,
            user_id=schedule.user_id,
            updated_at=schedule.updated_at,
            created_at=schedule.created_at,
        )

    @classmethod
    def of_array(cls, schedules: List[Schedule]) -> List[ScheduleResponse]:
        return [cls.of(schedule) for schedule in schedules]
