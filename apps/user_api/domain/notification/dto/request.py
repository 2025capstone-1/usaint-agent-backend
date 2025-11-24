from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Dict


class NotificationRequest(BaseModel):
    pass


class SubscribeRequest(NotificationRequest):
    """푸시 알림 구독 요청"""
    endpoint: str = Field(..., description="Push subscription endpoint")
    p256dh: str = Field(..., description="Push subscription p256dh key")
    auth: str = Field(..., description="Push subscription auth key")
    notification_types: Optional[Dict[str, bool]] = Field(
        default={"GRADE_CHECK": True, "CAFETERIA_CHECK": True, "SCHOLARSHIP_CHECK": True},
        description="알림 타입별 활성화 상태"
    )


class UpdateNotificationSettingsRequest(NotificationRequest):
    """알림 설정 업데이트 요청"""
    enabled: Optional[bool] = Field(None, description="전체 알림 활성화 여부")
    notification_types: Optional[Dict[str, bool]] = Field(
        None,
        description="알림 타입별 활성화 상태",
        examples=[{"GRADE_CHECK": True, "CAFETERIA_CHECK": False, "SCHOLARSHIP_CHECK": True}]
    )
