from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from lib.database import Base


class UsaintAccount(Base):
    __tablename__ = "usaint_account"

    usaint_account_id = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    id = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    user_id = Column(Integer, ForeignKey("user.user_id"),
                     nullable=False, unique=True)
    user = relationship("User", back_populates="usaint_account")

    # Creation
    @classmethod
    def create(cls, id: str, password: str, user_id: int):
        return cls(id=id, password=password, user_id=user_id)

    def update(self, id: str | None, password: str | None):
        if id:
            self.id = id
        if password:
            self.password = password

    # Utility
    def __str__(self):
        return f"[UsaintAccount] id: {self.usaint_account_id}, id: {self.id}, password: {self.password}, user_id: {self.user_id}"
