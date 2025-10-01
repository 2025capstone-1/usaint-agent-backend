from fastapi import HTTPException


class UsaintAccountNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="존재하지 않는 계정입니다.")
