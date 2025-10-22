from sqlalchemy.orm import Session
from apps.user_api.domain.usaint_account.dto.request import CreateUsaintAccountRequest, UpdateUsaintAccountRequest
from apps.user_api.domain.usaint_account.entity import UsaintAccount
from apps.user_api.domain.usaint_account.exception import UsaintAccountNotFound, UsaintAccountAlreadyExists
from lib.database import transactional
from lib.security import encrypt_password


def get_usaint_account_by_user_id(db: Session, user_id: int):
    """
    사용자 ID를 기반으로 U-Saint 계정 정보를 조회합니다.
    - Args:
        - db (Session): 데이터베이스 세션
        - user_id (int): 조회할 사용자의 ID
    - Raises:
        - UsaintAccountNotFound: 해당 사용자의 U-Saint 계정이 없을 경우
    - Returns:
        - UsaintAccount: 조회된 U-Saint 계정 엔티티
    """
    account = db.query(UsaintAccount).filter(
        UsaintAccount.user_id == user_id).first()
    if not account:
        raise UsaintAccountNotFound()
    return account


@transactional
def create_usaint_account(db: Session, user_id: int, request: CreateUsaintAccountRequest):
    """
    새로운 U-Saint 계정을 생성하고 데이터베이스에 저장합니다.
    비밀번호는 암호화하여 저장합니다.
    - Args:
        - db (Session): 데이터베이스 세션
        - user_id (int): 계정을 생성할 사용자의 ID
        - request (CreateUsaintAccountRequest): 생성할 계정 정보 DTO
    - Raises:
        - UsaintAccountAlreadyExists: 해당 사용자에게 이미 계정이 존재할 경우
    - Returns:
        - UsaintAccount: 새로 생성된 U-Saint 계정 엔티티
    """
    existing_account = db.query(UsaintAccount).filter(
        UsaintAccount.user_id == user_id).first()
    if existing_account:
        raise UsaintAccountAlreadyExists()

    # 비밀번호 암호화
    encrypted_password = encrypt_password(request.password)

    new_account = UsaintAccount.create(
        id=request.id,
        password=encrypted_password,  # 암호화된 비밀번호로 저장
        user_id=user_id
    )
    db.add(new_account)
    return new_account


@transactional
def update_usaint_account(db: Session, user_id: int, request: UpdateUsaintAccountRequest):
    """
    기존 U-Saint 계정 정보를 수정합니다.
    비밀번호가 변경될 경우, 암호화하여 저장합니다.
    - Args:
        - db (Session): 데이터베이스 세션
        - user_id (int): 계정을 수정할 사용자의 ID
        - request (UpdateUsaintAccountRequest): 수정할 계정 정보 DTO
    - Returns:
        - UsaintAccount: 수정된 U-Saint 계정 엔티티
    """
    account = get_usaint_account_by_user_id(db, user_id)

    # 업데이트할 비밀번호가 있을 경우에만 암호화
    encrypted_password = encrypt_password(
        request.password) if request.password else None
    account.update(request.id, encrypted_password)

    db.add(account)
    return account


@transactional
def delete_usaint_account(db: Session, user_id: int):
    """
    U-Saint 계정 정보를 데이터베이스에서 삭제합니다.
    - Args:
        - db (Session): 데이터베이스 세션
        - user_id (int): 계정을 삭제할 사용자의 ID
    """
    account = get_usaint_account_by_user_id(db, user_id)
    db.delete(account)
