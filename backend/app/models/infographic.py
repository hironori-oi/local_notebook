"""
Infographic model for storing generated infographic structures.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Infographic(Base):
    """
    Stores generated infographic structures with their JSON content.

    The structure column contains a JSON object with:
    - title: Main title
    - subtitle: Optional subtitle
    - sections: List of section objects with heading, icon_hint, key_points, etc.
    - footer_note: Optional footer text
    """
    __tablename__ = "infographics"

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
    structure = Column(JSONB, nullable=False)  # Generated infographic structure
    style_preset = Column(String(50), default="default")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    notebook = relationship("Notebook", backref="infographics")
    creator = relationship("User", backref="infographics")
