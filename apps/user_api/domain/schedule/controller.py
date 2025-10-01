from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.user_api.domain.auth.dto.token import TokenPayload
from apps.user_api.domain.auth.service import get_current_user
from apps.user_api.domain.schedule.entity import Schedule
from lib.database import get_db

router = APIRouter()
router_tag = ["Schedule API"]


@router.get("/public", tags=router_tag)
async def get_user(db: Session = Depends(get_db)):
    return "이 API는 로그인이 필요없습니다."


@router.get("/", tags=router_tag)
async def get(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    schedules = db.query(Schedule).all()
    return {"result": "hello?", "data": schedules}
