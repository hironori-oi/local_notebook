"""
Transcription model for YouTube video transcriptions.
"""

import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Transcription(Base):
    """
    Model for storing YouTube video transcription data.

    Attributes:
        id: Unique identifier
        user_id: Reference to the user who created this transcription
        youtube_url: Original YouTube URL
        video_id: YouTube video ID extracted from URL
        video_title: Title of the YouTube video
        raw_transcript: Raw transcription output from Whisper
        formatted_transcript: LLM-formatted transcript
        processing_status: Current status (pending, processing, completed, failed)
        processing_error: Error message if processing failed
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    youtube_url = Column(String(2048), nullable=False)
    video_id = Column(String(32), nullable=False)
    video_title = Column(String(500), nullable=True)

    raw_transcript = Column(Text, nullable=True)
    formatted_transcript = Column(Text, nullable=True)

    processing_status = Column(String(20), nullable=False, default="pending")
    processing_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user = relationship("User", backref="transcriptions")
