"""
Message model for storing chat messages.

Messages are now associated with a ChatSession for context management.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Message(Base):
    """
    Represents a single message in a chat conversation.

    Messages belong to a ChatSession and maintain the conversation history
    that can be sent to the LLM for context-aware responses.
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Session reference (required for new messages)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=True,  # Nullable for backward compatibility with existing data
        index=True
    )

    # Keep notebook_id for backward compatibility and easier queries
    notebook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # "user" or "assistant"
    role = Column(String(20), nullable=False)

    # Message status: pending, generating, completed, failed
    # For async chat processing - allows background generation
    status = Column(String(20), nullable=False, default="completed", index=True)

    # Error message if status is "failed"
    error_message = Column(Text, nullable=True)

    # Message content
    content = Column(Text, nullable=False)

    # JSON-encoded list of source references (e.g., ["doc1.pdf(p.3)", "doc2.pdf(p.5)"])
    source_refs = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
