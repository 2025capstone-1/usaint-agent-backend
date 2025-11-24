from __future__ import annotations
from datetime import datetime
from typing import List

from pydantic import BaseModel

from apps.user_api.domain.schedule.entity import Schedule


class ScheduleResponse(BaseModel):
    schedule_id: int
    cron: str
    task_type: str
    user_id: int
    restaurant_code: int | None
    updated_at: datetime
    created_at: datetime

    @classmethod
    def of(cls, schedule: Schedule):
        return cls(
            schedule_id=schedule.schedule_id,
            cron=schedule.cron,
            task_type=schedule.task_type,
            user_id=schedule.user_id,
            restaurant_code=schedule.restaurant_code,
            updated_at=schedule.updated_at,
            created_at=schedule.created_at,
        )

    @classmethod
    def of_array(cls, schedules: List[Schedule]) -> List[ScheduleResponse]:
        return [cls.of(schedule) for schedule in schedules]
