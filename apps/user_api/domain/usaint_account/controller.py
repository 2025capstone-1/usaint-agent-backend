from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.user_api.domain.auth.dto.token import TokenPayload
from apps.user_api.domain.auth.service import get_current_user
from apps.user_api.domain.usaint_account.dto.request import CreateUsaintAccountRequest, UpdateUsaintAccountRequest
from apps.user_api.domain.usaint_account.dto.response import UsaintAccountResponse
from apps.user_api.domain.usaint_account import service
from lib.database import get_db

router = APIRouter()
router_tag = ["UsaintAccount API"]


@router.post("/", tags=router_tag, status_code=status.HTTP_201_CREATED, response_model=UsaintAccountResponse)
async def create_my_usaint_account(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    request: CreateUsaintAccountRequest,
    db: Session = Depends(get_db),
):
    new_account = service.create_usaint_account(db, current_user.id, request)
    return UsaintAccountResponse.from_entity(new_account)


@router.get("/", tags=router_tag, response_model=UsaintAccountResponse)
async def get_my_usaint_account(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    account = service.get_usaint_account_by_user_id(db, current_user.id)
    return UsaintAccountResponse.from_entity(account)


@router.put("/", tags=router_tag, response_model=UsaintAccountResponse)
async def update_my_usaint_account(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    request: UpdateUsaintAccountRequest,
    db: Session = Depends(get_db),
):
    updated_account = service.update_usaint_account(
        db, current_user.id, request)
    return UsaintAccountResponse.from_entity(updated_account)


@router.delete("/", tags=router_tag, status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_usaint_account(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    service.delete_usaint_account(db, current_user.id)
    return
