from sqlalchemy import Column, Integer, String, ForeignKey, Enum, JSON, DateTime
from sqlalchemy.orm import relationship
from app.core.db import Base
from datetime import datetime 
import enum

class StatusEnum(str, enum.Enum):
    pending = "pending"
    replied = "replied"

class CartSubmission(Base):
    __tablename__ = "cart_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(StatusEnum), default=StatusEnum.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    cart_items = Column(JSON, default=list)
    user = relationship("User", back_populates="cart_submissions")
    def __repr__(self):
        return f"<CartSubmission(user_id={self.user_id}, status={self.status})>"