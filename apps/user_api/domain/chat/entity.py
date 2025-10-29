from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from lib.database import Base


class Chat(Base):
    __tablename__ = "chat"

    chat_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content = Column(Text, nullable=False)
    sender = Column(String(255), nullable=False)  # 'user' or 'agent'
    type = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Foreign Keys
    chat_room_id = Column(Integer, ForeignKey(
        "chat_room.chat_room_id"), nullable=False)

    # Relationships
    chat_room = relationship("ChatRoom", back_populates="chats")

    @staticmethod
    def create(chat_room_id: int, content: str, sender: str, type: str = None):
        return Chat(
            chat_room_id=chat_room_id,
            content=content,
            sender=sender,
            type=type,
        )

    def __str__(self):
        return (
            f"[Chat] chat_id: {self.chat_id}, chat_room_id: {self.chat_room_id}, "
            f"sender: {self.sender}, content: {self.content}"
        )
