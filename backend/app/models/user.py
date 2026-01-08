import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    role = Column(String(20), nullable=False, default="user")  # "admin" or "user"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"

    # Relationships
    chat_sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
