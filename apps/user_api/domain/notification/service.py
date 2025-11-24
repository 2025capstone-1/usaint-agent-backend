from sqlalchemy.orm import Session
from pywebpush import webpush, WebPushException
import json
from typing import Optional, Dict, List
import urllib3
import ssl
import certifi

from apps.user_api.domain.notification.dto.request import (
    SubscribeRequest,
    UpdateNotificationSettingsRequest,
)
from apps.user_api.domain.notification.entity import PushSubscription, NotificationHistory
from apps.user_api.domain.notification.exception import (
    SubscriptionNotFound,
    SubscriptionAlreadyExists,
)
from lib.env import get_env

# SSL 검증 경고 비활성화 (개발 환경용)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# SSL 검증을 우회하기 위한 monkey patch
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class SSLContextAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

# 전역 requests 세션에 SSL 우회 어댑터 적용
_original_request = requests.Session.request

def _patched_request(self, *args, **kwargs):
    if 'verify' not in kwargs:
        kwargs['verify'] = False
    return _original_request(self, *args, **kwargs)

requests.Session.request = _patched_request


def get_vapid_keys() -> dict:
    """환경변수에서 VAPID 키를 가져오고 올바르게 로드합니다."""
    import os
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    from py_vapid import Vapid01 as Vapid

    # private_key.pem 파일이 있으면 파일에서 읽기
    private_key_path = os.path.join(os.getcwd(), "private_key.pem")
    if os.path.exists(private_key_path):
        print(f"✅ Loading VAPID private key from file: {private_key_path}")
        with open(private_key_path, "rb") as f:
            private_key_pem = f.read()
    else:
        # 환경 변수에서 읽기
        private_key_str = get_env("VAPID_PRIVATE_KEY")
        print(f"⚠️ Loading VAPID private key from env (length: {len(private_key_str)})")

        # .env 파일에서 \n이 문자열로 저장되어 있으면 실제 줄바꿈으로 변환
        if "\\n" in private_key_str:
            print("🔄 Converting \\n to actual newlines")
            private_key_str = private_key_str.replace("\\n", "\n")

        private_key_pem = private_key_str.encode('utf-8')

    # cryptography로 private key 로드
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,
            backend=default_backend()
        )

        # Vapid 객체 생성
        vapid = Vapid()
        vapid.private_key = private_key

        # PEM 형식 문자열로 직렬화 (pywebpush가 문자열을 기대함)
        private_key_pem_str = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        print("✅ VAPID private key loaded successfully")

        return {
            "vapid": vapid,
            "private_key": private_key_pem_str,
            "public_key": get_env("VAPID_PUBLIC_KEY"),
            "claim_email": get_env("VAPID_CLAIM_EMAIL"),
        }
    except Exception as e:
        print(f"❌ Failed to load VAPID private key: {e}")
        import traceback
        traceback.print_exc()
        raise


def get_vapid_public_key() -> str:
    """VAPID 공개키를 반환합니다."""
    return get_env("VAPID_PUBLIC_KEY")


def subscribe_push_notification(
    db: Session, user_id: int, request: SubscribeRequest
) -> PushSubscription:
    """푸시 알림 구독을 생성합니다."""

    print(f"🔍 [DEBUG] subscribe_push_notification called with user_id={user_id}")

    # 사용자가 존재하는지 확인
    from apps.user_api.domain.user.entity import User
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        print(f"❌ [ERROR] User with user_id={user_id} does not exist in database!")
        raise Exception(f"User with id {user_id} not found")
    else:
        print(f"✅ [DEBUG] User found: {user.username} (id={user_id})")

    # 기존 구독이 있는지 확인
    existing_subscription = db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id
    ).first()

    if existing_subscription:
        # 기존 구독이 있으면 업데이트
        existing_subscription.endpoint = request.endpoint
        existing_subscription.p256dh = request.p256dh
        existing_subscription.auth = request.auth
        existing_subscription.enabled = True
        if request.notification_types:
            existing_subscription.notification_types = json.dumps(request.notification_types)

        db.commit()
        db.refresh(existing_subscription)
        print(f"✅ 푸시 구독이 업데이트되었습니다: user_id={user_id}")
        return existing_subscription

    # 새 구독 생성
    new_subscription = PushSubscription.create(
        user_id=user_id,
        endpoint=request.endpoint,
        p256dh=request.p256dh,
        auth=request.auth,
    )

    if request.notification_types:
        new_subscription.notification_types = json.dumps(request.notification_types)

    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)
    print(f"✅ 새로운 푸시 구독이 생성되었습니다: user_id={user_id}")
    return new_subscription


def unsubscribe_push_notification(db: Session, user_id: int) -> bool:
    """푸시 알림 구독을 삭제합니다."""
    subscription = db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id
    ).first()

    if not subscription:
        raise SubscriptionNotFound()

    db.delete(subscription)
    db.commit()
    print(f"✅ 푸시 구독이 삭제되었습니다: user_id={user_id}")
    return True


def get_subscription(db: Session, user_id: int) -> Optional[PushSubscription]:
    """사용자의 푸시 구독 정보를 조회합니다."""
    return db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id
    ).first()


def update_notification_settings(
    db: Session, user_id: int, request: UpdateNotificationSettingsRequest
) -> PushSubscription:
    """알림 설정을 업데이트합니다."""
    subscription = db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id
    ).first()

    if not subscription:
        raise SubscriptionNotFound()

    if request.enabled is not None:
        subscription.enabled = request.enabled

    if request.notification_types is not None:
        # 기존 설정과 병합
        current_types = json.loads(subscription.notification_types) if isinstance(subscription.notification_types, str) else subscription.notification_types
        current_types.update(request.notification_types)
        subscription.notification_types = json.dumps(current_types)

    db.commit()
    db.refresh(subscription)
    print(f"✅ 알림 설정이 업데이트되었습니다: user_id={user_id}")
    return subscription


def get_active_subscriptions(
    db: Session, task_type: Optional[str] = None
) -> List[PushSubscription]:
    """활성화된 푸시 구독 목록을 조회합니다."""
    subscriptions = db.query(PushSubscription).filter(
        PushSubscription.enabled == True
    ).all()

    if task_type:
        # 특정 task_type에 대한 알림이 활성화된 구독만 필터링
        filtered = []
        for sub in subscriptions:
            notification_types = json.loads(sub.notification_types) if isinstance(sub.notification_types, str) else sub.notification_types
            if notification_types.get(task_type, False):
                filtered.append(sub)
        return filtered

    return subscriptions


def send_push_notification(
    db: Session,
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict] = None,
    task_type: Optional[str] = None
) -> bool:
    """단일 사용자에게 푸시 알림을 전송합니다."""

    subscription = db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id,
        PushSubscription.enabled == True
    ).first()

    # 알림을 보낼 수 없는 경우에도 내역은 저장 (is_sent=False)
    is_sent = False

    if not subscription:
        print(f"⚠️ 활성화된 푸시 구독이 없습니다: user_id={user_id}")
        # 내역 저장
        _save_notification_history(db, user_id, title, body, task_type, data, is_sent=False)
        return False

    # task_type이 지정된 경우, 해당 타입의 알림이 활성화되어 있는지 확인
    if task_type:
        notification_types = json.loads(subscription.notification_types) if isinstance(subscription.notification_types, str) else subscription.notification_types
        if not notification_types.get(task_type, False):
            print(f"⚠️ {task_type} 알림이 비활성화되어 있습니다: user_id={user_id}")
            # 내역 저장
            _save_notification_history(db, user_id, title, body, task_type, data, is_sent=False)
            return False

    # 푸시 메시지 구성
    payload = {
        "title": title,
        "body": body,
        "icon": "/icon.png",  # 프론트엔드에 아이콘 파일 필요
        "badge": "/badge.png",  # 프론트엔드에 배지 파일 필요
    }

    if data:
        payload["data"] = data

    # VAPID 키 가져오기
    vapid_keys = get_vapid_keys()

    # 푸시 전송 (py_vapid를 직접 사용하여 구현)
    try:
        import base64
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from http_ece import encrypt
        import requests
        from urllib.parse import urlparse

        # VAPID 헤더 생성
        vapid = vapid_keys["vapid"]
        endpoint_url = subscription.endpoint
        parsed = urlparse(endpoint_url)
        audience = f"{parsed.scheme}://{parsed.netloc}"

        # VAPID 클레임 생성
        vapid_claims = {
            "sub": vapid_keys["claim_email"],
            "aud": audience,
            "exp": int(__import__('time').time()) + 43200  # 12시간
        }

        # VAPID 헤더 생성 (vapid 객체 사용)
        vapid_headers = vapid.sign(vapid_claims)

        # 페이로드 암호화
        payload_json = json.dumps(payload).encode('utf-8')

        # p256dh와 auth를 base64 디코딩
        p256dh_bytes = base64.urlsafe_b64decode(subscription.p256dh + '==')
        auth_bytes = base64.urlsafe_b64decode(subscription.auth + '==')

        # http_ece를 사용하여 암호화
        encrypted = encrypt(
            payload_json,
            private_key=vapid.private_key,
            dh=p256dh_bytes,
            auth_secret=auth_bytes,
            salt=None,
            version='aes128gcm'
        )

        # HTTP 헤더 구성
        headers = {
            'TTL': '86400',
            'Content-Encoding': 'aes128gcm',
            'Authorization': vapid_headers['Authorization'],
            'Crypto-Key': vapid_headers.get('Crypto-Key', ''),
        }

        # Content-Encoding에 따라 헤더 조정
        if 'Crypto-Key' in headers and not headers['Crypto-Key']:
            del headers['Crypto-Key']

        # 푸시 전송 (SSL 검증 비활성화)
        response = requests.post(
            endpoint_url,
            data=encrypted,
            headers=headers,
            verify=False  # SSL 검증 비활성화
        )

        # 응답 확인
        if response.status_code == 201:
            print(f"✅ 푸시 알림 전송 성공: user_id={user_id}, title={title}")
            is_sent = True
            # 내역 저장
            _save_notification_history(db, user_id, title, body, task_type, data, is_sent=True)
            return True
        elif response.status_code in [410, 404]:
            print(f"⚠️ 만료된 구독 삭제: user_id={user_id}, status={response.status_code}")
            db.delete(subscription)
            db.commit()
            # 내역 저장
            _save_notification_history(db, user_id, title, body, task_type, data, is_sent=False)
            return False
        else:
            print(f"❌ 푸시 알림 전송 실패: user_id={user_id}, status={response.status_code}, response={response.text}")
            # 내역 저장
            _save_notification_history(db, user_id, title, body, task_type, data, is_sent=False)
            return False

    except Exception as e:
        print(f"❌ 푸시 알림 전송 중 예외 발생: user_id={user_id}, error={e}")
        import traceback
        traceback.print_exc()
        # 내역 저장
        _save_notification_history(db, user_id, title, body, task_type, data, is_sent=False)
        return False


def _save_notification_history(
    db: Session,
    user_id: int,
    title: str,
    body: str,
    task_type: Optional[str] = None,
    data: Optional[Dict] = None,
    is_sent: bool = True
) -> NotificationHistory:
    """알림 내역을 저장합니다."""
    data_str = json.dumps(data) if data else None

    notification = NotificationHistory.create(
        user_id=user_id,
        title=title,
        body=body,
        task_type=task_type,
        data=data_str,
        is_sent=is_sent,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)
    print(f"✅ 알림 내역 저장됨: notification_id={notification.notification_id}, user_id={user_id}, is_sent={is_sent}")
    return notification


def get_notification_history(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[NotificationHistory]:
    """사용자의 알림 내역을 조회합니다."""
    return db.query(NotificationHistory).filter(
        NotificationHistory.user_id == user_id
    ).order_by(
        NotificationHistory.created_at.desc()
    ).limit(limit).offset(offset).all()


def get_unread_notification_count(db: Session, user_id: int) -> int:
    """읽지 않은 알림 개수를 조회합니다."""
    return db.query(NotificationHistory).filter(
        NotificationHistory.user_id == user_id,
        NotificationHistory.is_read == False
    ).count()


def mark_notification_as_read(
    db: Session,
    user_id: int,
    notification_id: int
) -> NotificationHistory:
    """알림을 읽음 처리합니다."""
    notification = db.query(NotificationHistory).filter(
        NotificationHistory.notification_id == notification_id,
        NotificationHistory.user_id == user_id
    ).first()

    if not notification:
        raise Exception(f"Notification not found: notification_id={notification_id}")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    print(f"✅ 알림 읽음 처리: notification_id={notification_id}")
    return notification


def mark_all_notifications_as_read(db: Session, user_id: int) -> int:
    """모든 알림을 읽음 처리합니다."""
    count = db.query(NotificationHistory).filter(
        NotificationHistory.user_id == user_id,
        NotificationHistory.is_read == False
    ).update({"is_read": True})

    db.commit()
    print(f"✅ 모든 알림 읽음 처리: user_id={user_id}, count={count}")
    return count


def send_bulk_push_notifications(
    db: Session,
    notifications: List[Dict],
    task_type: Optional[str] = None
) -> Dict[str, int]:
    """여러 사용자에게 푸시 알림을 일괄 전송합니다.

    Args:
        notifications: [{"user_id": int, "title": str, "body": str, "data": dict}, ...]
        task_type: 알림 타입 필터

    Returns:
        {"success": int, "failed": int}
    """
    results = {"success": 0, "failed": 0}

    for notification in notifications:
        success = send_push_notification(
            db=db,
            user_id=notification["user_id"],
            title=notification["title"],
            body=notification["body"],
            data=notification.get("data"),
            task_type=task_type
        )

        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

    print(f"📊 일괄 푸시 알림 전송 완료: {results}")
    return results
