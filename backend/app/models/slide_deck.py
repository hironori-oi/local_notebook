"""
SlideDeck model for storing generated slide deck outlines and PPTX file paths.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class SlideDeck(Base):
    """
    Stores generated slide deck outlines with their JSON content and PPTX file path.

    The outline column contains a JSON object with:
    - title: Presentation title
    - slides: List of slide objects with title, bullets, speaker_notes, visual_hint, etc.
    """
    __tablename__ = "slide_decks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    topic = Column(String(500), nullable=True)  # Original user prompt/topic
    outline = Column(JSONB, nullable=False)  # Generated slide outline structure
    pptx_path = Column(String(500), nullable=True)  # Path to generated PPTX file
    slide_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    notebook = relationship("Notebook", backref="slide_decks")
    creator = relationship("User", backref="slide_decks")
