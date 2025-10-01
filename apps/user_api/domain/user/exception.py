from fastapi import HTTPException


class UserNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="존재하지 않는 사용자입니다.")
