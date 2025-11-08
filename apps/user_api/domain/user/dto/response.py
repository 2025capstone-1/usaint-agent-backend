from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from apps.user_api.domain.user.entity import User


class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    @staticmethod
    def of(user: User):
        return UserProfileResponse(
            id=user.user_id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        )
