"""CouncilChatSession model for council chat conversations."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CouncilChatSession(Base):
    """
    Represents a chat session within a council.

    Sessions allow users to maintain separate conversation contexts,
    with the ability to select specific meetings for RAG context.
    """

    __tablename__ = "council_chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    council_id = Column(
        UUID(as_uuid=True),
        ForeignKey("councils.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=True)
    # Array of meeting UUIDs selected for RAG context
    selected_meeting_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    council = relationship("Council", back_populates="chat_sessions")
    user = relationship("User", backref="council_chat_sessions")
    messages = relationship(
        "CouncilMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CouncilMessage.created_at",
    )
