"""MinuteDocument model for linking minutes to source documents."""

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MinuteDocument(Base):
    """Junction table linking minutes to source documents."""

    __tablename__ = "minute_documents"

    minute_id = Column(
        UUID(as_uuid=True),
        ForeignKey("minutes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    minute = relationship("Minute", back_populates="document_links")
    document = relationship("Source")
