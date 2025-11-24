from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.user_api.domain.auth.dto.token import TokenPayload
from apps.user_api.domain.auth.service import get_current_user
from apps.user_api.domain.notification import service as notification_service
from apps.user_api.domain.notification.dto.request import (
    SubscribeRequest,
    UpdateNotificationSettingsRequest,
)
from apps.user_api.domain.notification.dto.response import (
    PushSubscriptionResponse,
    VapidPublicKeyResponse,
    NotificationHistoryResponse,
)
from lib.database import get_db

router = APIRouter()
router_tag = ["Notification API"]


@router.get("/vapid-public-key", tags=router_tag)
async def get_vapid_public_key():
    """VAPID 공개키 조회 (클라이언트에서 구독 시 필요)"""
    public_key = notification_service.get_vapid_public_key()
    return VapidPublicKeyResponse(vapid_public_key=public_key)


@router.post("/subscribe", tags=router_tag, status_code=201)
async def subscribe_notification(
    request: SubscribeRequest,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """푸시 알림 구독 등록"""
    subscription = notification_service.subscribe_push_notification(
        db, current_user.id, request
    )
    return PushSubscriptionResponse.of(subscription)


@router.delete("/unsubscribe", tags=router_tag, status_code=204)
async def unsubscribe_notification(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """푸시 알림 구독 해제"""
    notification_service.unsubscribe_push_notification(db, current_user.id)
    return True


@router.get("/subscription", tags=router_tag)
async def get_subscription(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """현재 사용자의 푸시 구독 정보 조회"""
    subscription = notification_service.get_subscription(db, current_user.id)
    if not subscription:
        return None
    return PushSubscriptionResponse.of(subscription)


@router.patch("/settings", tags=router_tag)
async def update_notification_settings(
    request: UpdateNotificationSettingsRequest,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """알림 설정 업데이트 (타입별 on/off 등)"""
    subscription = notification_service.update_notification_settings(
        db, current_user.id, request
    )
    return PushSubscriptionResponse.of(subscription)


@router.get("/history", tags=router_tag)
async def get_notification_history(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """알림 내역 조회"""
    history = notification_service.get_notification_history(
        db, current_user.id, limit, offset
    )
    return NotificationHistoryResponse.of_array(history)


@router.get("/history/unread-count", tags=router_tag)
async def get_unread_notification_count(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """읽지 않은 알림 개수 조회"""
    count = notification_service.get_unread_notification_count(db, current_user.id)
    return {"count": count}


@router.patch("/history/{notification_id}/read", tags=router_tag)
async def mark_notification_as_read(
    notification_id: int,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """알림 읽음 처리"""
    notification = notification_service.mark_notification_as_read(
        db, current_user.id, notification_id
    )
    return NotificationHistoryResponse.of(notification)


@router.patch("/history/read-all", tags=router_tag)
async def mark_all_notifications_as_read(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """모든 알림 읽음 처리"""
    count = notification_service.mark_all_notifications_as_read(db, current_user.id)
    return {"count": count}
