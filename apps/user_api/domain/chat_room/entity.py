from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from lib.database import Base


class ChatRoom(Base):
    __tablename__ = "chat_room"

    chat_room_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    summary = Column(Text, nullable=True)
    last_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="chat_rooms")
    chats = relationship(
        "Chat", back_populates="chat_room", cascade="all, delete-orphan"
    )

    @staticmethod
    def create(user_id: int, summary: str = None, last_content: str = None):
        return ChatRoom(
            user_id=user_id,
            summary=summary,
            last_content=last_content,
        )

    def __str__(self):
        return (
            f"[ChatRoom] chat_room_id: {self.chat_room_id}, user_id: {self.user_id}, "
            f"summary: {self.summary}, last_content: {self.last_content}"
        )
