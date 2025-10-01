from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from lib.database import Base


class ChatRoom(Base):
    __tablename__ = "chat_room"

    chat_room_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    last_content = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=True)
    user = relationship("User", back_populates="chat_rooms")

    schedule = relationship("Schedule", back_populates="chat_rooms")
    schedule_id = Column(Integer, ForeignKey("schedule.schedule_id"), nullable=True)

    chats = relationship("Chat", back_populates="chat_room")

    # Creation
    @classmethod
    def create(cls, user_id: int, schedule_id: Optional[int]):
        return cls(user_id=user_id, schedule_id=schedule_id)

    # Utility
    def __str__(self):
        return f"[ChatRoom] id: {self.chat_room_id}, last_content: {self.last_content}, user_id: {self.user_id}, schedule_id: {self.schedule_id}"
