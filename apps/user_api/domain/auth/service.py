from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from passlib.hash import argon2
from sqlalchemy.orm import Session

from apps.user_api.domain.auth.dto.request import SignInRequest, SignUpRequest
from apps.user_api.domain.auth.dto.token import TokenPayload
from apps.user_api.domain.auth.exception import AlreadyExistUser, NotAuthenticated
from apps.user_api.domain.user.entity import User
from lib.database import transactional
from lib.env import get_env

bearer_scheme = HTTPBearer(auto_error=True)

BCRYPT_SECRET = get_env("BCRYPT_SECRET")
JWT_SECRET = get_env("JWT_SECRET")
JWT_ALGORITHM = get_env("JWT_ALGORITHM")
ACCESS_TOKEN_TTL_MINUTES = int(get_env("ACCESS_TOKEN_TTL_MINUTES"))


def signup(db: Session, request: SignUpRequest):

    # 이 함수의 scope가 트랜잭션의 scope가 됩니다.
    @transactional
    def _signup(db: Session):
        encrypted_password = argon2.hash(request.password)
        new_user = request.to_entity(encrypted_password)

        exist_user = db.query(User).filter(User.email == new_user.email).first()
        if exist_user:
            raise AlreadyExistUser()

        db.add(new_user)
        return new_user

    user = _signup(db)
    db.refresh(user)

    return user


def signin(db: Session, request: SignInRequest):
    user = db.query(User).filter(User.email == request.email).first()
    if user == None:
        raise NotAuthenticated()

    is_password_correct = argon2.verify(request.password, user.password)
    if is_password_correct == False:
        raise NotAuthenticated()

    payload = TokenPayload(id=user.user_id, authority="ROLE_USER")
    return create_access_token(payload)


def create_access_token(token_data: TokenPayload):
    data = vars(token_data)

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    data.update({"exp": expire})

    token = jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def get_current_user(token: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        payload: dict[str, str] = jwt.decode(
            token.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )

        user_id = payload.get("id")
        authority = payload.get("authority")

        if user_id is None:
            raise NotAuthenticated()

        if authority != "ROLE_USER":
            raise NotAuthenticated()

        return TokenPayload(id=user_id, authority=authority)

    except InvalidTokenError:
        raise NotAuthenticated()
