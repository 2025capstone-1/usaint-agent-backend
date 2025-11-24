from __future__ import annotations

# from dataclasses import dataclass

from croniter import croniter
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ScheduleRequest(BaseModel):
    pass


class CreateScheduleRequest(ScheduleRequest):
    cron: str = Field(
        ..., description="Cron expression for the schedule", examples=["0 4 * * *"]
    )

    task_type: str = Field(
        ..., description="AI가 분류한 작업 타입", examples=["GRADE_CHECK"]
    )

    restaurant_code: Optional[int] = Field(
        None, description="학식 조회용 식당 코드 (1-7)", examples=[1]
    )

    @field_validator("cron")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: {v}")
        return v


class UpdateScheduleRequest(ScheduleRequest):
    cron: Optional[str] = Field(
        None,
        description="Updated cron expression for the schedule",
        examples=["0 4 * * *"],
    )

    restaurant_code: Optional[int] = Field(
        None, description="학식 조회용 식당 코드 (1-7)", examples=[1]
    )

    @field_validator("cron")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        # cron이 none일 수도 있으므로 체크
        if v is None:
            return v

        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: {v}")
        return v
