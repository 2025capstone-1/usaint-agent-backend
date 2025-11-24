from datetime import datetime
from typing import Literal

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from lib.database import Base

Authority = Literal["ROLE_USER"]


class User(Base):
    __tablename__ = "user"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    authority: Authority = Column(String(100), nullable=False, default="ROLE_USER")

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    usaint_account = relationship(
        "UsaintAccount", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    schedules = relationship("Schedule", back_populates="user")
    chat_rooms = relationship("ChatRoom", back_populates="user", cascade="all, delete-orphan")
    push_subscriptions = relationship("PushSubscription", back_populates="user", cascade="all, delete-orphan")
    notification_history = relationship("NotificationHistory", back_populates="user", cascade="all, delete-orphan")

    # Creation
    @classmethod
    def create(cls, username: str, email: str, password: str):
        return cls(username=username, email=email, password=password)

    # Utility
    def __str__(self):
        return f"[User] id: {self.user_id}, name: {self.username}, email: {self.email}, password: {self.password}"
