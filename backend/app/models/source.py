"""Source model for uploaded documents."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Source(Base):
    """Uploaded document source (PDF, DOCX, TXT, MD)."""

    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    folder_id = Column(
        UUID(as_uuid=True),
        ForeignKey("source_folders.id", ondelete="CASCADE"),
        nullable=True,
    )
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    folder = relationship("SourceFolder", back_populates="sources")

    # Content processing fields for email generation
    full_text = Column(Text, nullable=True)  # Extracted full text from document
    formatted_text = Column(Text, nullable=True)  # LLM-formatted text
    summary = Column(Text, nullable=True)  # LLM-generated summary
    processing_status = Column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)  # Error message if processing failed
