from __future__ import annotations
from pydantic import BaseModel


class CreateUsaintAccountRequest(BaseModel):
    id: str
    password: str


class UpdateUsaintAccountRequest(BaseModel):
    id: str | None = None
    password: str | None = None
