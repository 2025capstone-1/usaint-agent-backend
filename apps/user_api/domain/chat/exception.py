from fastapi import HTTPException


class ChatNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="존재하지 않는 채팅입니다.")
