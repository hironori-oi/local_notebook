"""
ChatSession model for managing conversation sessions.

Each notebook can have multiple chat sessions, allowing users to
maintain separate conversation contexts.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ChatSession(Base):
    """
    Represents a chat session within a notebook.

    A session groups related messages together, allowing the LLM to maintain
    context across multiple exchanges within the same conversation thread.
    """

    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Session title - auto-generated from first message or user-defined
    title = Column(String(255), nullable=True)

    # Optional summary of the conversation (for future use)
    summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    notebook = relationship("Notebook", back_populates="chat_sessions")
    user = relationship("User", back_populates="chat_sessions")
