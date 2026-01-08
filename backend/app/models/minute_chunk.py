"""MinuteChunk model for RAG vector storage of minute content."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.config import settings
from app.db.base import Base


class MinuteChunk(Base):
    """Chunked minute content with embeddings for RAG search."""

    __tablename__ = "minute_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    minute_id = Column(
        UUID(as_uuid=True),
        ForeignKey("minutes.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIM))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    minute = relationship("Minute", back_populates="chunks")
