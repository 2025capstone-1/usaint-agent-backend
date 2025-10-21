from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from datetime import datetime
from apps.user_api.domain.usaint_account.entity import UsaintAccount


class UsaintAccountResponse(BaseModel):
    usaint_account_id: int
    id: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(account: UsaintAccount) -> "UsaintAccountResponse":
        return UsaintAccountResponse(
            usaint_account_id=account.usaint_account_id,
            id=account.id,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
