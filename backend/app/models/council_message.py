"""CouncilMessage model for storing council chat messages."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CouncilMessage(Base):
    """
    Represents a single message in a council chat conversation.

    Messages belong to a CouncilChatSession and store the conversation
    history along with source references from RAG retrieval.
    """

    __tablename__ = "council_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("council_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    # JSON array of source references (e.g., [{"meeting_id": "...", "type": "materials", "excerpt": "..."}])
    source_refs = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("CouncilChatSession", back_populates="messages")
