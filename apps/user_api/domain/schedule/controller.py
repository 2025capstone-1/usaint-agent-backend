from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.user_api.domain.auth.dto.token import TokenPayload
from apps.user_api.domain.auth.service import get_current_user
#from apps.user_api.domain.schedule.entity import Schedule

from apps.user_api.domain.schedule import service as schedule_service
from apps.user_api.domain.schedule.dto.request import CreateScheduleRequest, UpdateScheduleRequest

from lib.database import get_db

router = APIRouter()
router_tag = ["Schedule API"]


@router.get("/public", tags=router_tag)
async def get_user(db: Session = Depends(get_db)):
    return "이 API는 로그인이 필요없습니다."


# 아래 API들은 로그인이 필요합니다.

# 새로운 스케줄 생성 요청시
@router.post("/", tags=router_tag, status_code=201)
async def create_schedule(
    request: CreateScheduleRequest,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    새로운 스케줄을 생성합니다.
    """
    new_schedule = schedule_service.create_schedule(db, current_user.id, request)
    return {"result": "success", "data": new_schedule}  

# 스케줄 조회 요청시
@router.get("/", tags=router_tag)
async def get_my_schedules(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    현재 사용자의 모든 스케줄을 조회합니다.
    """
    schedules = schedule_service.get_schedules_by_user_id(db, current_user.id)
    return {"result": "success", "data": schedules}

# 스케줄 수정 요청시
@router.put("/{schedule_id}", tags=router_tag)
async def update_schedule(
    schedule_id: int,
    request: UpdateScheduleRequest,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    특정 스케줄을 수정합니다.
    """
    updated_schedule = schedule_service.update_schedule(db, schedule_id, current_user.id, request)
    return {"result": "success", "data": updated_schedule}

# 스케줄 삭제 요청시
@router.delete("/{schedule_id}", tags=router_tag, status_code=204)
async def delete_schedule(
    schedule_id: int,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    특정 스케줄을 삭제합니다.
    """
    schedule_service.delete_schedule(db, schedule_id, current_user.id)
    return