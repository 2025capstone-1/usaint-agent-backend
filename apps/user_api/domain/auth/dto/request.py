from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from apps.user_api.domain.user.entity import User


@dataclass
class SignInRequest(BaseModel):
    email: str
    password: str


@dataclass
class SignUpRequest(BaseModel):
    username: str
    email: str
    password: str

    def to_entity(self, encrypted_password: str):
        return User.create(
            username=self.username, email=self.email, password=encrypted_password
        )
