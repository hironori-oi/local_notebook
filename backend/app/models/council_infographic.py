"""
Council Infographic model for storing generated infographic structures for councils.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CouncilInfographic(Base):
    """
    Stores generated infographic structures for council meetings.

    The structure column contains a JSON object with:
    - title: Main title
    - subtitle: Optional subtitle
    - sections: List of section objects with heading, icon_hint, key_points, etc.
    - footer_note: Optional footer text
    """

    __tablename__ = "council_infographics"

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
        nullable=True,  # Optional - can be council-wide or meeting-specific
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
    structure = Column(JSONB, nullable=False)  # Generated infographic structure
    style_preset = Column(String(50), default="default")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    council = relationship("Council", back_populates="infographics")
    meeting = relationship("CouncilMeeting", back_populates="infographics")
    creator = relationship("User", backref="council_infographics")
