from fastapi import HTTPException


class ChatRoomNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="존재하지 않는 채팅방입니다.")
