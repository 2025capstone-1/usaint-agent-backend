from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from lib.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscription"

    subscription_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Push subscription 정보
    endpoint = Column(Text, nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)

    # 활성화 여부
    enabled = Column(Boolean, nullable=False, default=True)

    # 알림 타입별 설정 (JSON 형태로 저장: {"GRADE_CHECK": true, "CAFETERIA_CHECK": true, "SCHOLARSHIP_CHECK": true})
    notification_types = Column(Text, nullable=False, default='{"GRADE_CHECK": true, "CAFETERIA_CHECK": true, "SCHOLARSHIP_CHECK": true}')

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    user = relationship("User", back_populates="push_subscriptions")

    # Creation
    @classmethod
    def create(cls, user_id: int, endpoint: str, p256dh: str, auth: str):
        return cls(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        )

    # Utility
    def __str__(self):
        return f"[PushSubscription] id: {self.subscription_id}, user_id: {self.user_id}, enabled: {self.enabled}"


class NotificationHistory(Base):
    __tablename__ = "notification_history"

    notification_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 알림 정보
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(Text, nullable=True)  # JSON 형태로 저장
    task_type = Column(String(100), nullable=True)  # GRADE_CHECK, CAFETERIA_CHECK, SCHOLARSHIP_CHECK 등

    # 전송 상태
    is_sent = Column(Boolean, nullable=False, default=True)  # 전송 성공 여부
    is_read = Column(Boolean, nullable=False, default=False)  # 읽음 여부

    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    user = relationship("User", back_populates="notification_history")

    # Creation
    @classmethod
    def create(
        cls,
        user_id: int,
        title: str,
        body: str,
        task_type: str = None,
        data: str = None,
        is_sent: bool = True,
    ):
        return cls(
            user_id=user_id,
            title=title,
            body=body,
            task_type=task_type,
            data=data,
            is_sent=is_sent,
        )

    # Utility
    def __str__(self):
        return f"[NotificationHistory] id: {self.notification_id}, user_id: {self.user_id}, title: {self.title}, is_sent: {self.is_sent}, is_read: {self.is_read}"
