from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from lib.database import Base


class Schedule(Base):
    __tablename__ = "schedule"

    schedule_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 일단 cron으로 했는데, 필요하면 추가/수정해주세요!
    cron = Column(String(255), nullable=True)

    # ai에게 전할 자연어
    content = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=True)
    user = relationship("User", back_populates="schedules")
    chat_room = relationship("ChatRoom", back_populates="schedules")
    chat_room_id = Column(Integer, ForeignKey("chat_room.chat_room_id"), nullable=True)

    # Creation
    @classmethod
    def create(cls, cron: str, content: str, user_id: int):
        return cls(cron=cron, content=content, user_id=user_id)

    # Utility
    def __str__(self):
        return f"[Schedule] id: {self.schedule_id}, cron: {self.cron}, content: {self.content}, user_id: {self.user_id}"
