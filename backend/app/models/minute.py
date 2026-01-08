"""Minute model for text-based meeting minutes."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Minute(Base):
    """Meeting minutes stored as text (not file-based)."""

    __tablename__ = "minutes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Content processing fields for email generation
    formatted_content = Column(Text, nullable=True)  # LLM-formatted text
    summary = Column(Text, nullable=True)  # LLM-generated summary
    processing_status = Column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)  # Error message if processing failed

    # Relationships
    chunks = relationship(
        "MinuteChunk", back_populates="minute", cascade="all, delete-orphan"
    )
    document_links = relationship(
        "MinuteDocument", back_populates="minute", cascade="all, delete-orphan"
    )
