from pydantic import BaseModel
from datetime import datetime
from apps.user_api.domain.usaint_account.entity import UsaintAccount
from lib.security import decrypt_password


class UsaintAccountResponse(BaseModel):
    usaint_account_id: int
    id: str
    password: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(account: UsaintAccount) -> "UsaintAccountResponse":
        # 응답 생성 시점에 비밀번호를 복호화
        decrypted_pwd = decrypt_password(account.password)

        return UsaintAccountResponse(
            usaint_account_id=account.usaint_account_id,
            id=account.id,
            password=decrypted_pwd,  # 복호화된 비밀번호를 전달
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
