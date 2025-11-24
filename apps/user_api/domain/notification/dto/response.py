from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Optional
import json

from pydantic import BaseModel

from apps.user_api.domain.notification.entity import PushSubscription, NotificationHistory


class PushSubscriptionResponse(BaseModel):
    subscription_id: int
    user_id: int
    enabled: bool
    notification_types: Dict[str, bool]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, subscription: PushSubscription):
        # JSON string을 dictionary로 변환
        notification_types = json.loads(subscription.notification_types) if isinstance(subscription.notification_types, str) else subscription.notification_types

        return cls(
            subscription_id=subscription.subscription_id,
            user_id=subscription.user_id,
            enabled=subscription.enabled,
            notification_types=notification_types,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )

    @classmethod
    def of_array(cls, subscriptions: List[PushSubscription]) -> List[PushSubscriptionResponse]:
        return [cls.of(subscription) for subscription in subscriptions]


class VapidPublicKeyResponse(BaseModel):
    """VAPID 공개키 응답"""
    vapid_public_key: str


class NotificationHistoryResponse(BaseModel):
    """알림 내역 응답"""
    notification_id: int
    user_id: int
    title: str
    body: str
    data: Optional[Dict]
    task_type: Optional[str]
    is_sent: bool
    is_read: bool
    created_at: datetime

    @classmethod
    def of(cls, notification: NotificationHistory):
        # JSON string을 dictionary로 변환
        data = json.loads(notification.data) if notification.data and isinstance(notification.data, str) else notification.data

        return cls(
            notification_id=notification.notification_id,
            user_id=notification.user_id,
            title=notification.title,
            body=notification.body,
            data=data,
            task_type=notification.task_type,
            is_sent=notification.is_sent,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )

    @classmethod
    def of_array(cls, notifications: List[NotificationHistory]) -> List[NotificationHistoryResponse]:
        return [cls.of(notification) for notification in notifications]
