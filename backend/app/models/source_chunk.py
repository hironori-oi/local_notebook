import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.config import settings
from app.db.base import Base


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    page_number = Column(Integer, nullable=True)
    # Dimension configured via EMBEDDING_DIM environment variable
    # embeddinggemma:300m outputs 768 dimensions, PLaMo-Embedding-1B outputs 2048
    embedding = Column(Vector(dim=settings.EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
