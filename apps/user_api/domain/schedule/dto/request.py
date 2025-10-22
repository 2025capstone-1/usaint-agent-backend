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
    content: str = Field(
        ...,
        description="Content to be scheduled",
        examples=["이번 학기 성적표 조회해줘"],
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
    content: Optional[str] = Field(
        None,
        description="Updated content to be scheduled",
        examples=["이번 학기 성적표 조회해줘"],
    )

    @field_validator("cron")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: {v}")
        return v
