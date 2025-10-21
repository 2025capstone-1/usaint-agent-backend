from sqlalchemy.orm import Session
from apps.user_api.domain.usaint_account.dto.request import CreateUsaintAccountRequest, UpdateUsaintAccountRequest
from apps.user_api.domain.usaint_account.entity import UsaintAccount
from apps.user_api.domain.usaint_account.exception import UsaintAccountNotFound, UsaintAccountAlreadyExists  # 추가
from lib.database import transactional


def get_usaint_account_by_user_id(db: Session, user_id: int):
    account = db.query(UsaintAccount).filter(
        UsaintAccount.user_id == user_id).first()
    if not account:
        raise UsaintAccountNotFound()
    return account


@transactional
def create_usaint_account(db: Session, user_id: int, request: CreateUsaintAccountRequest):
    # 이미 계정이 있는지 확인
    existing_account = db.query(UsaintAccount).filter(
        UsaintAccount.user_id == user_id).first()
    if existing_account:
        raise UsaintAccountAlreadyExists()

    new_account = UsaintAccount.create(
        id=request.id,
        password=request.password,
        user_id=user_id
    )
    db.add(new_account)
    return new_account


@transactional
def update_usaint_account(db: Session, user_id: int, request: UpdateUsaintAccountRequest):
    account = get_usaint_account_by_user_id(db, user_id)
    account.update(request.id, request.password)
    db.add(account)
    return account


@transactional
def delete_usaint_account(db: Session, user_id: int):
    account = get_usaint_account_by_user_id(db, user_id)
    db.delete(account)
