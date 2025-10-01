from pydantic import BaseModel

from apps.user_api.domain.user.entity import Authority


class TokenPayload(BaseModel):
    id: int | None = None
    authority: Authority = "ROLE_USER"
