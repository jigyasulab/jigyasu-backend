from sqlalchemy import Column, Integer, String,ForeignKey
from sqlalchemy.orm import relationship
from app.core.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    org_name = Column(String, nullable=True)
    role = Column(String, default="user")  # Use String instead of Enum
    hashed_password = Column(String)
    name = Column(String, default="Anonymous User")
    cart_submissions = relationship("CartSubmission", back_populates="user")
    role_requests = relationship("RoleUpgradeRequestTable", back_populates="user")
    refresh_token = Column(String, nullable=True)

    def __repr__(self):
        return f"<User(username={self.username}, role={self.role})>"

class RoleUpgradeRequestTable(Base):
    __tablename__ = "role_upgrade_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_role = Column(String, nullable=False)  # Use String instead of Enum
    internal_role = Column(String, nullable=True)  # Internal role as string
    status = Column(String, default="pending")
    user = relationship("User", back_populates="role_requests")
