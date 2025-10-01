from fastapi import HTTPException


class NotAuthenticated(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=401, detail="이메일 또는 비밀번호가 일치하지 않습니다."
        )


class AlreadyExistUser(HTTPException):
    def __init__(self):
        super().__init__(status_code=406, detail="이미 존재하는 계정입니다.")
