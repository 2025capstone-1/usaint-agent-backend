from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.user_api.domain.auth.dto.request import SignInRequest, SignUpRequest
from apps.user_api.domain.auth.dto.response import SigninResponse
from apps.user_api.domain.auth.service import signin, signup
from apps.user_api.domain.user.entity import User
from lib.database import get_db
from lib.env import get_env

router = APIRouter()
router_tag = ["Auth API"]

TOKEN_TYPE = get_env("JWT_TYPE")


@router.post("/signin", tags=router_tag)
def post_login(request: SignInRequest, db: Session = Depends(get_db)):
    token = signin(db, request)

    return SigninResponse(token_type=TOKEN_TYPE, access_token=token)


@router.post("/signup", tags=router_tag)
def post_signup(request: SignUpRequest, db: Session = Depends(get_db)):
    new_user = signup(db, request)
    return {"result": "hello?", "data": new_user.user_id}
