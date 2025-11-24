from fastapi import HTTPException


class SubscriptionNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="푸시 알림 구독이 존재하지 않습니다.")


class SubscriptionAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(status_code=409, detail="이미 푸시 알림 구독이 존재합니다.")
