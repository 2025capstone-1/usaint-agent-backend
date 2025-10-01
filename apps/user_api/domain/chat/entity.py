from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from lib.database import Base


class Chat(Base):
    __tablename__ = "chat"

    chat_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content = Column(Text, nullable=False)
    sender = Column(String(255), nullable=False)
    type = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    chat_room_id = Column(Integer, ForeignKey("chat_room.chat_room_id"), nullable=True)
    chat_room = relationship("ChatRoom", back_populates="chats")

    # Creation
    @classmethod
    def create(
        cls, content: str, sender: str, chat_room_id: str, type: Optional[str] = None
    ):
        return cls(content=content, sender=sender, chat_room_id=chat_room_id, type=type)

    # Utility
    def __str__(self):
        return f"[Chat] id: {self.chat_id}, content: {self.content}, sender: {self.sender} type: {self.type} chat_room_id: {self.chat_room_id}"
