"""CouncilNote model for council and meeting level notes."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CouncilNote(Base):
    """
    Represents a note associated with a council or specific meeting.

    If meeting_id is NULL, it's a council-level note.
    If meeting_id is set, it's a meeting-specific note.
    """

    __tablename__ = "council_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    council_id = Column(
        UUID(as_uuid=True),
        ForeignKey("councils.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meeting_id = Column(
        UUID(as_uuid=True),
        ForeignKey("council_meetings.id", ondelete="CASCADE"),
        nullable=True,  # NULL = council-level note
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    council = relationship("Council", back_populates="notes")
    meeting = relationship("CouncilMeeting", back_populates="notes")
    user = relationship("User", backref="council_notes")
