from fastapi import HTTPException


class ScheduleNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="존재하지 않는 스케줄입니다.")

class ScheduleAccessDenied(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail="해당 스케줄에 대한 권한이 없습니다.")

