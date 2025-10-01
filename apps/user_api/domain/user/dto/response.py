from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel

from apps.user_api.domain.user.entity import User


@dataclass
class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: date

    def of(user: User):
        return UserProfileResponse(
            id=user.user_id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        )
